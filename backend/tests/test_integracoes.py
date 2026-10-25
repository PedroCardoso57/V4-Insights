from __future__ import annotations

import logging
from datetime import date, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select

from app.integrations import registry
from app.integrations.base import PermissionProviderError, RetryableProviderError
from app.models import ContaAnuncio, Integracao, MetricaDiaria, Segredo, SyncJob
from app.sync import service
from tests.fakes import TOKEN_SECRETO, FakeProvider


@pytest.fixture
def fake():  # type: ignore[no-untyped-def]
    p = FakeProvider()
    registry.override_provider("meta", lambda: p)
    yield p
    registry.override_provider("meta", None)


def _conectar(cli, cliente_id, integracao_id=None) -> str:  # type: ignore[no-untyped-def]
    body = {"cliente_id": str(cliente_id)}
    if integracao_id:
        body["integracao_id"] = str(integracao_id)
    r = cli.post("/integracoes/meta/autorizar", json=body)
    assert r.status_code == 200, r.text
    state = parse_qs(urlsplit(r.json()["authorization_url"]).query)["state"][0]
    r = cli.get(f"/integracoes/meta/callback?state={state}&code=xyz", follow_redirects=False)
    assert r.status_code == 302, r.text
    return parse_qs(urlsplit(r.headers["location"]).query)["integracao"][0]


@pytest.fixture
def cenario(factory, fake, enfileirados):  # type: ignore[no-untyped-def]
    u = factory.usuario("analista")
    c = factory.cliente("Cliente", membros=(u,))
    cli = factory.login(u)
    iid = _conectar(cli, c.id)
    return cli, c, iid


def _executar(enfileirados) -> list[str]:  # type: ignore[no-untyped-def]
    out = []
    while enfileirados:
        job_id, _ = enfileirados.pop(0)
        out.append(service.run_job(job_id))
    return out


def test_conexao_lista_contas_e_token_criptografado(cenario, db) -> None:
    cli, c, iid = cenario
    integ = db.get(Integracao, iid)
    assert integ.status == "pendente"
    assert integ.referencia_credencial.startswith("secret:")
    assert TOKEN_SECRETO not in integ.referencia_credencial
    cipher = db.scalar(select(Segredo.ciphertext))
    assert TOKEN_SECRETO.encode() not in cipher
    r = cli.get(f"/integracoes/{iid}/contas")
    assert [x["id_externo"] for x in r.json()] == ["111", "222"]
    lista = cli.get(f"/integracoes?cliente_id={c.id}").json()
    assert TOKEN_SECRETO not in str(lista)


def test_selecao_de_contas_dispara_carga_historica(cenario, enfileirados, db) -> None:
    cli, _, iid = cenario
    r = cli.post(
        f"/integracoes/{iid}/contas",
        json={
            "contas": [
                {
                    "id_externo": "111",
                    "carga_historica_dias": 5,
                    "mapeamento_conversoes": {"action_types": ["purchase"]},
                }
            ]
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ativa"
    assert (
        cli.post(f"/integracoes/{iid}/contas", json={"contas": [{"id_externo": "999"}]}).status_code
        == 400
    )
    assert _executar(enfileirados) == ["sucesso"]
    assert db.scalar(select(func.count()).select_from(MetricaDiaria)) == 6
    m = db.scalars(select(MetricaDiaria)).first()
    assert m.conversoes == 2 and m.valor_conversoes == 40
    conta = db.scalar(select(ContaAnuncio))
    assert conta.ultima_sincronizacao_em is not None and conta.dados_ate is not None


def test_sync_duplicado_nao_duplica_linhas(cenario, enfileirados, db) -> None:
    cli, _, iid = cenario
    cli.post(
        f"/integracoes/{iid}/contas",
        json={"contas": [{"id_externo": "111", "carga_historica_dias": 3}]},
    )
    _executar(enfileirados)
    body = {
        "data_inicio": (date.today() - timedelta(days=3)).isoformat(),
        "data_fim": date.today().isoformat(),
    }
    j1 = cli.post(f"/integracoes/{iid}/sincronizar", json=body).json()
    j2 = cli.post(f"/integracoes/{iid}/sincronizar", json=body).json()
    assert j1[0]["id"] == j2[0]["id"]  # chave idempotente
    assert len(enfileirados) == 1
    _executar(enfileirados)
    antes = db.scalar(select(func.count()).select_from(MetricaDiaria))
    # mesmo reprocessando, o UPSERT mantém uma linha por chave
    service.upsert_metricas(
        db,
        db.scalar(select(ContaAnuncio)),
        "meta",
        list(FakeProvider().fetch_metrics({}, "111", "campanha", date.today(), date.today(), {})),
    )
    db.commit()
    assert db.scalar(select(func.count()).select_from(MetricaDiaria)) == antes
    # sem mapeamento explícito, conversões ficam ausentes
    assert db.scalars(select(MetricaDiaria)).first().conversoes is None


def test_quota_tem_retry_controlado(cenario, fake, enfileirados, db) -> None:
    cli, _, iid = cenario
    fake.erros = [RetryableProviderError("HTTP 429 rate limit", retry_after=7)]
    cli.post(
        f"/integracoes/{iid}/contas",
        json={"contas": [{"id_externo": "111", "carga_historica_dias": 1}]},
    )
    job_id, _ = enfileirados.pop(0)
    assert service.run_job(job_id) == "pendente"
    assert enfileirados == [(job_id, 7)]
    job = db.get(SyncJob, job_id)
    assert job.tentativas == 1 and "429" in job.erro
    enfileirados.clear()
    assert service.run_job(job_id) == "sucesso"


def test_retry_tem_limite(cenario, fake, enfileirados, db) -> None:
    cli, _, iid = cenario
    fake.erros = [RetryableProviderError("HTTP 503") for _ in range(10)]
    cli.post(
        f"/integracoes/{iid}/contas",
        json={"contas": [{"id_externo": "111", "carga_historica_dias": 1}]},
    )
    job_id, _ = enfileirados[0]
    status = None
    for _ in range(10):
        enfileirados.clear()
        status = service.run_job(job_id)
        if status == "erro":
            break
    assert status == "erro"
    assert db.get(SyncJob, job_id).tentativas == 5


def test_erro_de_permissao_nao_repete(cenario, fake, enfileirados, db) -> None:
    cli, _, iid = cenario
    fake.erros = [PermissionProviderError(f"HTTP 403 token {TOKEN_SECRETO} inválido")]
    cli.post(
        f"/integracoes/{iid}/contas",
        json={"contas": [{"id_externo": "111", "carga_historica_dias": 1}]},
    )
    job_id, _ = enfileirados.pop(0)
    assert service.run_job(job_id) == "erro"
    assert enfileirados == []
    db.expire_all()
    assert db.get(Integracao, iid).status == "erro"
    assert TOKEN_SECRETO not in db.get(SyncJob, job_id).erro  # erro sanitizado


def test_revogacao_bloqueia_novas_coletas(cenario, fake, enfileirados, db) -> None:
    cli, _, iid = cenario
    cli.post(
        f"/integracoes/{iid}/contas",
        json={"contas": [{"id_externo": "111", "carga_historica_dias": 1}]},
    )
    pendente, _ = enfileirados.pop(0)
    r = cli.post(f"/integracoes/{iid}/revogar")
    assert r.status_code == 200 and r.json()["status"] == "revogada"
    assert fake.revogado
    assert service.run_job(pendente) == "cancelado"
    assert fake.chamadas == 0
    assert cli.post(f"/integracoes/{iid}/sincronizar").status_code == 409
    assert db.scalar(select(func.count()).select_from(Segredo)) == 0
    service.agendar_incrementais(db)
    assert enfileirados == []


def test_revogacao_durante_coleta_interrompe(cenario, fake, enfileirados, db) -> None:
    cli, _, iid = cenario
    cli.post(
        f"/integracoes/{iid}/contas",
        json={"contas": [{"id_externo": "111", "carga_historica_dias": 900}]},
    )
    job_id, _ = enfileirados.pop(0)
    chamadas = {"n": 0}

    def revogar_no_meio() -> None:
        chamadas["n"] += 1
        if chamadas["n"] == 600:
            cli.post(f"/integracoes/{iid}/revogar")

    fake.on_fetch = revogar_no_meio
    assert service.run_job(job_id) == "cancelado"
    assert db.scalar(select(func.count()).select_from(MetricaDiaria)) == 500  # só 1º lote


def test_pausar_e_retomar(cenario, enfileirados, db) -> None:
    cli, _, iid = cenario
    cli.post(f"/integracoes/{iid}/contas", json={"contas": [{"id_externo": "111"}]})
    job_id, _ = enfileirados.pop(0)
    assert cli.post(f"/integracoes/{iid}/pausar").json()["status"] == "pausada"
    assert service.run_job(job_id) == "cancelado"
    assert cli.post(f"/integracoes/{iid}/retomar").json()["status"] == "ativa"


def test_reconectar_mantem_contas(cenario, enfileirados) -> None:
    cli, c, iid = cenario
    cli.post(f"/integracoes/{iid}/contas", json={"contas": [{"id_externo": "111"}]})
    cli.post(f"/integracoes/{iid}/revogar")
    novo = _conectar(cli, c.id, iid)
    assert novo == iid
    integ = cli.get(f"/integracoes?cliente_id={c.id}").json()[0]
    assert integ["status"] == "ativa" and len(integ["contas"]) == 1


def test_agendador_incremental(cenario, enfileirados, db) -> None:
    cli, _, iid = cenario
    cli.post(
        f"/integracoes/{iid}/contas",
        json={"contas": [{"id_externo": "111", "carga_historica_dias": 2}]},
    )
    assert service.agendar_incrementais(db) == 0  # já existe job em aberto
    _executar(enfileirados)
    assert service.agendar_incrementais(db) == 0  # sincronizado recentemente
    conta = db.scalar(select(ContaAnuncio))
    conta.ultima_sincronizacao_em = service.utcnow() - timedelta(hours=7)
    db.commit()
    assert service.agendar_incrementais(db) == 1
    assert service.agendar_incrementais(db) == 0  # idempotente


def test_callback_exige_state_do_mesmo_usuario(factory, fake, enfileirados) -> None:
    u1, u2 = factory.usuario("analista"), factory.usuario("analista")
    c = factory.cliente(membros=(u1, u2))
    a, b = factory.login(u1), factory.login(u2)
    url = a.post("/integracoes/meta/autorizar", json={"cliente_id": str(c.id)}).json()
    state = parse_qs(urlsplit(url["authorization_url"]).query)["state"][0]
    assert b.get(f"/integracoes/meta/callback?state={state}&code=x").status_code == 400


def test_cliente_arquivado_nao_aceita_integracao(factory, fake) -> None:
    u = factory.usuario("analista")
    c = factory.cliente(membros=(u,), status="arquivado")
    r = factory.login(u).post("/integracoes/meta/autorizar", json={"cliente_id": str(c.id)})
    assert r.status_code == 409


def test_isolamento_e_permissoes(cenario, factory) -> None:
    _, _, iid = cenario
    outro = factory.login(factory.usuario("analista"))
    assert outro.get("/integracoes").json() == []
    assert outro.get(f"/integracoes/{iid}/jobs").status_code == 404
    assert outro.post(f"/integracoes/{iid}/revogar").status_code == 404
    vis = factory.usuario("visualizador")
    assert factory.login(vis).get("/integracoes").status_code == 403


def test_logs_nao_expoem_segredos(cenario, fake, enfileirados, caplog) -> None:
    cli, _, iid = cenario
    from app.logging_config import SanitizingFilter

    caplog.handler.addFilter(SanitizingFilter())
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("teste").warning("falha: access_token=%s", TOKEN_SECRETO)
        fake.erros = [PermissionProviderError(f"Bearer {TOKEN_SECRETO}")]
        cli.post(
            f"/integracoes/{iid}/contas",
            json={"contas": [{"id_externo": "111", "carga_historica_dias": 1}]},
        )
        _executar(enfileirados)
    assert TOKEN_SECRETO not in caplog.text
