"""M04: mapeamento de conversões por cliente."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import Auditoria, ContaAnuncio, Integracao, MetricaDiaria, SyncJob

HOJE = date.today()


def _detalhe(compra: int, lead: int, valor_compra: str) -> dict:  # type: ignore[type-arg]
    return {
        "acoes": {
            "purchase": {"value": str(compra), "7d_click": str(compra)},
            "lead": {"value": str(lead)},
        },
        "valores": {"purchase": {"value": valor_compra}},
    }


@pytest.fixture
def cenario(factory, db):  # type: ignore[no-untyped-def]
    analista = factory.usuario("analista")
    visual = factory.usuario("visualizador")
    c = factory.cliente("Loja", membros=(analista, visual))
    integ = Integracao(cliente_id=c.id, plataforma="meta_ads", status="conectada")
    db.add(integ)
    db.flush()
    conta = ContaAnuncio(
        integracao_id=integ.id, conta_externa_id="act1", nome="Meta Loja", moeda="BRL"
    )
    db.add(conta)
    db.flush()
    for i, (compra, lead, valor) in enumerate([(2, 5, "300"), (1, 3, "120")]):
        db.add(
            MetricaDiaria(
                conta_anuncio_id=conta.id,
                data=HOJE - timedelta(days=i),
                nivel="campanha",
                entidade_externa_id="camp",
                investimento=Decimal(100),
                impressoes=1000,
                cliques=10,
                conversoes_detalhe=_detalhe(compra, lead, valor),
            )
        )
    # Nível anúncio repete o mesmo dado: não pode entrar nos totais.
    db.add(
        MetricaDiaria(
            conta_anuncio_id=conta.id,
            data=HOJE,
            nivel="anuncio",
            entidade_externa_id="ad",
            conversoes_detalhe=_detalhe(2, 5, "300"),
        )
    )
    db.commit()
    return factory, c, conta, analista, visual


def test_lista_acoes_com_totais_dos_ultimos_30_dias(cenario) -> None:
    factory, c, conta, _, visual = cenario
    r = factory.login(visual).get(f"/clientes/{c.id}/conversoes")
    assert r.status_code == 200
    (item,) = r.json()["contas"]
    assert item["conta_anuncio_id"] == str(conta.id)
    assert item["janelas"] == ["1d_click", "7d_click", "28d_click", "1d_view"]
    acoes = {a["action_type"]: a for a in item["acoes"]}
    assert Decimal(acoes["lead"]["quantidade"]) == 8
    assert Decimal(acoes["purchase"]["quantidade"]) == 3
    assert Decimal(acoes["purchase"]["valor"]) == 420
    assert acoes["lead"]["valor"] is None
    assert [a["action_type"] for a in item["acoes"]] == ["lead", "purchase"]  # mais frequente antes


def test_salvar_recalcula_cpa_e_registra_auditoria(cenario, db) -> None:
    factory, c, conta, analista, _ = cenario
    cli = factory.login(analista)
    body = {"action_types": ["purchase", "lead"], "acao_valor": ["purchase"]}
    r = cli.put(f"/clientes/{c.id}/conversoes/{conta.id}", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["linhas_recalculadas"] == 3 and r.json()["ressincronizando"] is False
    resumo = cli.get(
        f"/clientes/{c.id}/metricas/resumo?inicio={HOJE - timedelta(days=5)}&fim={HOJE}"
    ).json()["atual"]
    assert Decimal(resumo["conversoes"]) == 11  # 3 compras + 8 leads
    assert Decimal(resumo["valor_conversoes"]) == 420  # só o valor das compras
    assert Decimal(resumo["cpa"]) == Decimal("18.1818")
    audit = db.query(Auditoria).filter_by(acao="alterar_mapeamento_conversoes").one()
    assert audit.metadados["depois"]["action_types"] == ["purchase", "lead"]

    # Salvar igual não recalcula nem audita de novo.
    r = cli.put(f"/clientes/{c.id}/conversoes/{conta.id}", json=body)
    assert r.json()["linhas_recalculadas"] == 0
    assert db.query(Auditoria).filter_by(acao="alterar_mapeamento_conversoes").count() == 1

    # Sem ações marcadas, conversões voltam a ficar ausentes (nunca zero).
    cli.put(f"/clientes/{c.id}/conversoes/{conta.id}", json={"action_types": []})
    resumo = cli.get(
        f"/clientes/{c.id}/metricas/resumo?inicio={HOJE - timedelta(days=5)}&fim={HOJE}"
    ).json()["atual"]
    assert resumo["conversoes"] is None and resumo["cpa"] is None


def test_trocar_janela_pede_nova_coleta(cenario, fila, db) -> None:
    factory, c, conta, analista, _ = cenario
    cli = factory.login(analista)
    r = cli.put(
        f"/clientes/{c.id}/conversoes/{conta.id}",
        json={"action_types": ["purchase"], "janela": "7d_click"},
    )
    assert r.status_code == 200 and r.json()["ressincronizando"] is True
    job = db.query(SyncJob).filter_by(conta_anuncio_id=conta.id, tipo="historico").one()
    assert any(j == job.id for j, _ in fila.sync)
    r = cli.put(
        f"/clientes/{c.id}/conversoes/{conta.id}",
        json={"action_types": ["purchase"], "janela": "7d_view"},
    )
    assert r.status_code == 422  # janela descontinuada pela Meta


def test_permissoes_e_isolamento(cenario, db) -> None:
    factory, c, conta, _, visual = cenario
    body = {"action_types": ["purchase"]}
    assert (
        factory.login(visual).put(f"/clientes/{c.id}/conversoes/{conta.id}", json=body).status_code
        == 403
    )
    outro = factory.login(factory.usuario("analista"))
    assert outro.get(f"/clientes/{c.id}/conversoes").status_code == 404
    assert outro.put(f"/clientes/{c.id}/conversoes/{conta.id}", json=body).status_code == 404
    # Conta de outro cliente pelo caminho deste cliente: 404.
    c2 = factory.cliente("Outro")
    admin = factory.login(factory.usuario("admin"))
    assert admin.put(f"/clientes/{c2.id}/conversoes/{conta.id}", json=body).status_code == 404
