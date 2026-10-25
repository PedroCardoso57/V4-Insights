from __future__ import annotations

import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import func, select

from app.core import oidc
from app.models import Sessao, Usuario

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OUTRA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeJWK:
    key = KEY.public_key()


class _FakeJWKS:
    def get_signing_key_from_jwt(self, token: str) -> _FakeJWK:
        return _FakeJWK()


def _id_token(
    nonce: str,
    *,
    sub: str = "sub-1",
    email: str = "ana@v4.com",
    verified: bool = True,
    aud: str = "client-id-teste",
    iss: str = "https://accounts.google.com",
    exp_delta: int = 3600,
    key: Any = KEY,
) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "iss": iss,
            "aud": aud,
            "sub": sub,
            "email": email,
            "email_verified": verified,
            "nonce": nonce,
            "iat": now,
            "exp": now + exp_delta,
            "name": "Ana",
        },
        key,
        algorithm="RS256",
    )


@pytest.fixture
def google(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(oidc, "_jwks_client", lambda url: _FakeJWKS())
    holder: dict[str, Any] = {}
    monkeypatch.setattr(
        oidc, "exchange_code", lambda code, verifier: {"id_token": holder["make"](holder["nonce"])}
    )

    def iniciar(anon, make=_id_token):  # type: ignore[no-untyped-def]
        r = anon.get("/auth/google/login", follow_redirects=False)
        assert r.status_code == 302
        q = parse_qs(urlsplit(r.headers["location"]).query)
        assert q["code_challenge_method"] == ["S256"]
        holder["nonce"] = q["nonce"][0]
        holder["make"] = make
        return q["state"][0]

    return iniciar


def test_login_sucesso_vincula_sub_e_cria_sessao(anon, google, factory, db) -> None:
    u = factory.usuario("analista", email="ana@v4.com")
    state = google(anon)
    r = anon.get(f"/auth/google/callback?state={state}&code=abc", follow_redirects=False)
    assert r.status_code == 302
    cookie = r.headers.get_list("set-cookie")
    sess = next(c for c in cookie if c.startswith("v4_session="))
    assert "HttpOnly" in sess and "SameSite=lax" in sess
    assert "id_token" not in " ".join(cookie) and "eyJ" not in sess  # sem tokens no cookie
    db.expire_all()
    assert db.get(Usuario, u.id).google_sub == "sub-1"
    me = anon.get("/auth/me")
    assert me.status_code == 200 and me.json()["email"] == "ana@v4.com"


def test_conta_nao_cadastrada_recebe_403_sem_criar_usuario(anon, google, db) -> None:
    state = google(anon)
    r = anon.get(f"/auth/google/callback?state={state}&code=abc", follow_redirects=False)
    assert r.status_code == 403
    assert db.scalar(select(func.count()).select_from(Usuario)) == 0


def test_usuario_inativo_recusado(anon, google, factory) -> None:
    factory.usuario("analista", email="ana@v4.com", ativo=False)
    state = google(anon)
    r = anon.get(f"/auth/google/callback?state={state}&code=abc")
    assert r.status_code == 403


def test_troca_de_sub_recusada(anon, google, factory) -> None:
    factory.usuario("analista", email="ana@v4.com", sub="sub-original")
    state = google(anon, make=lambda n: _id_token(n, sub="sub-invasor"))
    r = anon.get(f"/auth/google/callback?state={state}&code=abc")
    assert r.status_code == 403


def test_vinculo_por_sub_ignora_mudanca_de_email(anon, google, factory) -> None:
    factory.usuario("analista", email="antigo@v4.com", sub="sub-1")
    state = google(anon, make=lambda n: _id_token(n, sub="sub-1", email="novo@v4.com"))
    r = anon.get(f"/auth/google/callback?state={state}&code=abc", follow_redirects=False)
    assert r.status_code == 302


@pytest.mark.parametrize(
    "make",
    [
        lambda n: _id_token("nonce-errado"),
        lambda n: _id_token(n, verified=False),
        lambda n: _id_token(n, aud="outro-client"),
        lambda n: _id_token(n, iss="https://malicioso.example"),
        lambda n: _id_token(n, exp_delta=-3600),
        lambda n: _id_token(n, key=OUTRA_KEY),
    ],
)
def test_token_invalido_recusado(anon, google, factory, make) -> None:
    factory.usuario("analista", email="ana@v4.com")
    state = google(anon, make=make)
    r = anon.get(f"/auth/google/callback?state={state}&code=abc")
    assert r.status_code == 401


def test_state_incorreto_ou_reutilizado(anon, google, factory) -> None:
    factory.usuario("analista", email="ana@v4.com")
    state = google(anon)
    assert anon.get("/auth/google/callback?state=forjado&code=abc").status_code == 400
    assert (
        anon.get(
            f"/auth/google/callback?state={state}&code=abc", follow_redirects=False
        ).status_code
        == 302
    )
    assert anon.get(f"/auth/google/callback?state={state}&code=abc").status_code == 400


def test_logout_invalida_sessao_no_servidor(factory, db) -> None:
    u = factory.usuario("analista")
    c = factory.login(u)
    assert c.get("/auth/me").status_code == 200
    assert c.post("/auth/logout").status_code == 204
    db.expire_all()
    assert db.scalar(select(Sessao).where(Sessao.usuario_id == u.id)).revogada_em is not None
    token = db.scalar(select(Sessao).where(Sessao.usuario_id == u.id)).id
    assert token  # só o hash é persistido
    c.cookies.set("v4_session", c.cookies.get("v4_session") or "x")
    assert c.get("/auth/me").status_code == 401


def test_mutacao_exige_csrf_e_origin(factory) -> None:
    c = factory.login(factory.usuario("admin"))
    body = {"nome": "Novo", "email": "n@v4.com", "papel": "analista"}
    assert c.post("/usuarios", json=body, headers={"X-CSRF-Token": "errado"}).status_code == 403
    assert (
        c.post("/usuarios", json=body, headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    assert c.post("/usuarios", json=body).status_code == 201


def test_sem_sessao_401(anon) -> None:
    assert anon.get("/auth/me").status_code == 401
    assert anon.get("/clientes").status_code == 401


@pytest.mark.parametrize("papel", ["analista", "visualizador", "gestor"])
def test_somente_admin_cria_usuario(factory, papel) -> None:
    c = factory.login(factory.usuario(papel))
    r = c.post("/usuarios", json={"nome": "X Y", "email": "x@v4.com", "papel": "admin"})
    assert r.status_code == 403


def test_desativar_usuario_revoga_sessoes(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    alvo_u = factory.usuario("analista")
    alvo = factory.login(alvo_u)
    assert alvo.get("/auth/me").status_code == 200
    assert admin.patch(f"/usuarios/{alvo_u.id}", json={"ativo": False}).status_code == 200
    assert alvo.get("/auth/me").status_code == 401


def test_email_normalizado_e_duplicado(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    r = admin.post(
        "/usuarios", json={"nome": "Bia", "email": " Bia@V4.com ".strip(), "papel": "visualizador"}
    )
    assert r.status_code == 201 and r.json()["email"] == "bia@v4.com"
    r2 = admin.post(
        "/usuarios", json={"nome": "Bia", "email": "BIA@v4.com", "papel": "visualizador"}
    )
    assert r2.status_code == 409


def test_gestor_atribui_somente_clientes_da_carteira(factory) -> None:
    gestor_u = factory.usuario("gestor")
    analista = factory.usuario("analista")
    meu = factory.cliente("Meu", membros=(gestor_u,))
    alheio = factory.cliente("Alheio")
    g = factory.login(gestor_u)
    assert g.put(f"/usuarios/{analista.id}/clientes/{meu.id}").status_code == 204
    assert g.put(f"/usuarios/{analista.id}/clientes/{alheio.id}").status_code == 404
    admin = factory.login(factory.usuario("admin"))
    assert admin.put(f"/usuarios/{analista.id}/clientes/{alheio.id}").status_code == 204
    assert g.delete(f"/usuarios/{analista.id}/clientes/{meu.id}").status_code == 204
