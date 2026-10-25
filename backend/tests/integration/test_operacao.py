"""SPEC-07: rate limit, rotação de chave, LGPD, retenção, métricas e alertas."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
import respx
from cryptography.fernet import Fernet
from httpx import Response
from sqlalchemy import func, select

from app.core import crypto
from app.core.config import get_settings
from app.core.sessions import now
from app.models import (
    Auditoria,
    ContaAnuncio,
    CredencialIntegracao,
    Integracao,
    OAuthState,
    Sessao,
    SyncJob,
    Usuario,
)
from app.services import alertas, lgpd, retencao


@pytest.fixture
def config(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    s = get_settings()

    def definir(**kw):  # type: ignore[no-untyped-def]
        for k, v in kw.items():
            monkeypatch.setattr(s, k, v)

    return definir


def test_rate_limit_login_por_ip(anon, config) -> None:
    config(rate_limit_login="3/60")
    codigos = [anon.get("/auth/google/login", follow_redirects=False).status_code for _ in range(4)]
    assert codigos == [302, 302, 302, 429]
    r = anon.get("/auth/google/login", follow_redirects=False)
    assert r.json()["error"]["code"] == "RATE_LIMITED" and int(r.headers["retry-after"]) > 0


def test_rate_limit_operacoes_caras_por_usuario(factory, config) -> None:
    config(rate_limit_operacoes_caras="2/60")
    u = factory.usuario("analista")
    c = factory.cliente(membros=(u,))
    cli = factory.login(u)
    rid = cli.post("/relatorios", json={"cliente_id": str(c.id), "titulo": "Rel"}).json()["id"]
    codigos = [cli.post(f"/relatorios/{rid}/gerar").status_code for _ in range(3)]
    assert codigos == [202, 202, 429]
    # outro usuário tem sua própria cota
    outro = factory.usuario("analista")
    factory.cliente(membros=(outro,))
    assert factory.login(outro).post(f"/relatorios/{rid}/gerar").status_code == 404


def test_rotacao_de_chave_recifra_credenciais(db, factory, config) -> None:
    c = factory.cliente()
    integ = Integracao(cliente_id=c.id, plataforma="meta_ads", status="conectada")
    db.add(integ)
    db.flush()
    ref = crypto.store_secret(db, {"access_token": "tok"}, integracao_id=integ.id)
    db.commit()
    antiga = get_settings().encryption_key
    nova = Fernet.generate_key().decode()
    config(encryption_key=nova, encryption_keys_previous=[antiga])
    assert crypto.load_secret(db, ref) == {"access_token": "tok"}  # lê com a antiga
    assert crypto.rotacionar_chaves(db) == 1
    config(encryption_keys_previous=[])
    assert crypto.load_secret(db, ref) == {"access_token": "tok"}  # só a nova basta
    cred = db.scalar(select(CredencialIntegracao))
    assert b"tok" not in cred.ciphertext


def test_lgpd_exportar_e_anonimizar(db, factory, anon) -> None:
    u = factory.usuario("analista", email="Titular@V4.com", sub="sub-x")
    factory.cliente("Carteira", membros=(u,))
    cli = factory.login(u)
    cli.get("/auth/me")
    dados = lgpd.exportar(db, "titular@v4.com")
    assert dados["usuario"]["email"] == "Titular@V4.com"
    assert dados["carteira"][0]["nome"] == "Carteira" and dados["sessoes"]
    lgpd.anonimizar(db, "titular@v4.com")
    db.expire_all()
    anon_u = db.get(Usuario, u.id)
    assert not anon_u.ativo and anon_u.google_sub is None and "anonimizado" in anon_u.email
    assert cli.get("/auth/me").status_code == 401  # sessões revogadas
    assert db.scalar(select(func.count()).select_from(Sessao).where(Sessao.ip.is_not(None))) == 0
    with pytest.raises(lgpd.TitularNaoEncontrado):
        lgpd.exportar(db, "titular@v4.com")


def test_retencao_expurga_dados_vencidos(db, factory, config) -> None:
    config(sessions_retention_days=30, audit_retention_days=365)
    u = factory.usuario()
    db.add(
        Sessao(
            usuario_id=u.id,
            token_hash=uuid.uuid4().hex,
            csrf_hash="x",
            expira_em=now() - timedelta(days=40),
        )
    )
    db.add(
        Sessao(
            usuario_id=u.id,
            token_hash=uuid.uuid4().hex,
            csrf_hash="x",
            expira_em=now() + timedelta(hours=1),
        )
    )
    db.add(OAuthState(id=uuid.uuid4().hex, finalidade="login", expira_em=now() - timedelta(days=2)))
    db.add(Auditoria(acao="x", entidade="y", data_hora=now() - timedelta(days=400)))
    db.add(Auditoria(acao="x", entidade="y"))
    db.commit()
    assert retencao.expurgar(db) == {"sessoes": 1, "oauth_states": 1, "auditoria": 1}
    assert db.scalar(select(func.count()).select_from(Sessao)) == 1


def test_metricas_prometheus(anon, factory) -> None:
    anon.get("/health/live")
    texto = anon.get("/metrics").text
    assert 'v4_http_requests_total{method="GET",route="/health/live",status="200"}' in texto
    assert "v4_contas_desatualizadas" in texto and "v4_sync_jobs_24h" in texto


def test_alerta_sync_persistente_com_deduplicacao(db, factory, config) -> None:
    config(alert_webhook_url="https://hooks.exemplo.com/alerta", alert_sync_falhas_consecutivas=3)
    c = factory.cliente("Padaria")
    integ = Integracao(cliente_id=c.id, plataforma="meta_ads", status="conectada")
    db.add(integ)
    db.flush()
    conta = ContaAnuncio(integracao_id=integ.id, conta_externa_id="act9", nome="Conta")
    db.add(conta)
    db.flush()
    for i in range(3):
        db.add(
            SyncJob(
                integracao_id=integ.id,
                conta_anuncio_id=conta.id,
                tipo="incremental",
                status="erro",
                periodo_inicio=date.today(),
                periodo_fim=date.today(),
                idempotency_key=f"k{i}",
            )
        )
    db.commit()
    with respx.mock(assert_all_called=True) as mock:
        rota = mock.post("https://hooks.exemplo.com/alerta").mock(return_value=Response(200))
        assert alertas.verificar(db) == 1
        assert alertas.verificar(db) == 0  # silenciado: não repete o mesmo alerta
        assert rota.call_count == 1
        assert "act9" in rota.calls[0].request.content.decode()
