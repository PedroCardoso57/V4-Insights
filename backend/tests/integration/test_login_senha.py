from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import senhas
from app.models import Auditoria, Sessao, Usuario

SENHA = "Pao-de-queijo-2026"


def _com_senha(db: Session, u: Usuario, senha: str = SENHA) -> Usuario:
    u.senha_hash = senhas.gerar_hash(senha)
    db.commit()
    return u


def _login(anon, email: str, senha: str = SENHA, **extra):  # type: ignore[no-untyped-def]
    return anon.post("/auth/login", json={"email": email, "senha": senha, **extra})


def test_login_com_senha_cria_sessao_e_acessa_me(anon, factory, db) -> None:
    u = _com_senha(db, factory.usuario("gestor", email="Bia@V4.com"))
    r = _login(anon, "bia@v4.com")
    assert r.status_code == 204
    assert "v4_session" in r.cookies and "v4_csrf" in r.cookies
    me = anon.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"].lower() == "bia@v4.com" and me.json()["tem_senha"] is True
    db.expire_all()
    assert db.get(Usuario, u.id).ultimo_login_em is not None  # type: ignore[union-attr]
    acoes = db.scalars(select(Auditoria.acao).where(Auditoria.usuario_id == u.id)).all()
    assert "login" in acoes


def test_cookie_de_sessao_do_navegador_sem_manter_conectado(anon, factory, db) -> None:
    u = _com_senha(db, factory.usuario())
    r = _login(anon, u.email, manter_conectado=False)
    assert r.status_code == 204
    cookie = [h for h in r.headers.get_list("set-cookie") if h.startswith("v4_session=")][0]
    assert "Max-Age" not in cookie and "HttpOnly" in cookie


def test_respostas_iguais_para_falhas(anon, factory, db) -> None:
    com = _com_senha(db, factory.usuario())
    sem = factory.usuario()
    inativo = _com_senha(db, factory.usuario(ativo=False))
    respostas = [
        _login(anon, com.email, "senha-errada-123"),
        _login(anon, "ninguem@v4.com"),
        _login(anon, sem.email),
        _login(anon, inativo.email),
    ]
    assert {r.status_code for r in respostas} == {401}
    assert {r.json()["error"]["message"] for r in respostas} == {"E-mail ou senha inválidos."}
    assert all("v4_session" not in r.cookies for r in respostas)
    assert db.scalar(select(Sessao).where(Sessao.usuario_id == inativo.id)) is None


def test_login_exige_origin_permitida(anon, factory, db) -> None:
    u = _com_senha(db, factory.usuario())
    r = anon.post(
        "/auth/login",
        json={"email": u.email, "senha": SENHA},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


def test_limite_de_tentativas_por_email(anon, factory, db, monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "rate_limit_login_email", "3/900")
    u = _com_senha(db, factory.usuario())
    codigos = [_login(anon, u.email, "errada-errada").status_code for _ in range(3)]
    assert codigos == [401, 401, 401]
    assert _login(anon, u.email).status_code == 429  # nem a senha certa passa no bloqueio


def test_trocar_propria_senha_exige_atual_e_encerra_outras_sessoes(factory, db) -> None:
    u = _com_senha(db, factory.usuario())
    outra = factory.login(u)
    c = factory.login(u)
    errada = c.put("/auth/senha", json={"senha_atual": "errada", "nova_senha": "Nova-senha-forte"})
    assert errada.status_code == 400
    fraca = c.put("/auth/senha", json={"senha_atual": SENHA, "nova_senha": "curta"})
    assert fraca.status_code == 422
    r = c.put("/auth/senha", json={"senha_atual": SENHA, "nova_senha": "Nova-senha-forte"})
    assert r.status_code == 204
    assert c.get("/auth/me").status_code == 200
    assert outra.get("/auth/me").status_code == 401
    db.expire_all()
    assert senhas.verificar(db.get(Usuario, u.id).senha_hash, "Nova-senha-forte")  # type: ignore[union-attr]


def test_usuario_google_define_primeira_senha_sem_senha_atual(factory, anon) -> None:
    u = factory.usuario(sub="sub-x")
    c = factory.login(u)
    assert c.put("/auth/senha", json={"nova_senha": "Primeira-senha-ok"}).status_code == 204
    assert _login(anon, u.email, "Primeira-senha-ok").status_code == 204


def test_senha_igual_ao_email_recusada(factory) -> None:
    u = factory.usuario(email="carla.souza@v4.com")
    c = factory.login(u)
    r = c.put("/auth/senha", json={"nova_senha": "carla.souza@v4.com"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "WEAK_PASSWORD"


def test_admin_define_e_remove_senha_de_colaborador(factory, anon, db) -> None:
    admin = factory.login(factory.usuario("admin"))
    alvo = factory.usuario("analista")
    sessao_alvo = factory.login(alvo)
    r = admin.put(f"/usuarios/{alvo.id}/senha", json={"nova_senha": "Temporaria-123"})
    assert r.status_code == 204
    assert sessao_alvo.get("/auth/me").status_code == 401  # redefinição encerra sessões
    lista = admin.get("/usuarios").json()["items"]
    assert next(x for x in lista if x["id"] == str(alvo.id))["tem_senha"] is True
    assert _login(anon, alvo.email, "Temporaria-123").status_code == 204
    assert admin.delete(f"/usuarios/{alvo.id}/senha").status_code == 204
    assert _login(anon, alvo.email, "Temporaria-123").status_code == 401


def test_somente_admin_define_senha_de_outros(factory) -> None:
    gestor = factory.login(factory.usuario("gestor"))
    alvo = factory.usuario("analista")
    r = gestor.put(f"/usuarios/{alvo.id}/senha", json={"nova_senha": "Temporaria-123"})
    assert r.status_code == 403


def test_hash_nunca_aparece_nas_respostas(factory, db) -> None:
    u = _com_senha(db, factory.usuario("admin"))
    c = factory.login(u)
    corpo = c.get("/auth/me").text + c.get("/usuarios").text + c.get(f"/usuarios/{u.id}").text
    assert "argon2" not in corpo and "senha_hash" not in corpo
