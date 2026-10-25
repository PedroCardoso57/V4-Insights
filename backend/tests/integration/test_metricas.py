from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.models import ContaAnuncio, Integracao, MetricaDiaria

D1, D2, D3 = date(2026, 3, 1), date(2026, 3, 2), date(2026, 3, 8)


@pytest.fixture
def dados(factory, db):  # type: ignore[no-untyped-def]
    u = factory.usuario("visualizador")
    c = factory.cliente("Cliente", membros=(u,))
    integ = Integracao(cliente_id=c.id, plataforma="meta_ads", status="conectada")
    integ_g = Integracao(cliente_id=c.id, plataforma="google_ads", status="conectada")
    db.add_all([integ, integ_g])
    db.flush()
    conta = ContaAnuncio(integracao_id=integ.id, conta_externa_id="1", nome="Meta", moeda="BRL")
    conta_g = ContaAnuncio(
        integracao_id=integ_g.id, conta_externa_id="2", nome="Google", moeda="BRL"
    )
    db.add_all([conta, conta_g])
    db.flush()

    def m(conta, data, ent, inv, imp, cli, conv=None, valor=None, nivel="campanha"):  # type: ignore[no-untyped-def]
        db.add(
            MetricaDiaria(
                conta_anuncio_id=conta.id,
                data=data,
                nivel=nivel,
                entidade_externa_id=ent,
                campanha_externa_id=ent,
                campanha_nome=f"Camp {ent}",
                investimento=Decimal(inv),
                impressoes=imp,
                cliques=cli,
                conversoes=conv,
                valor_conversoes=valor,
            )
        )

    db.refresh(conta)
    db.refresh(conta_g)
    # Período atual: 01/03 a 08/03
    m(conta, D1, "a", "100.00", 10000, 200, Decimal(10), Decimal(500))
    m(conta, D2, "a", "50.00", 5000, 100, Decimal(5), Decimal(100))
    m(conta_g, D3, "g", "150.00", 15000, 0)  # sem conversões mapeadas
    # Nível anúncio do mesmo gasto: não pode entrar na soma por campanha
    m(conta, D1, "ad1", "100.00", 10000, 200, nivel="anuncio")
    # Período anterior (21/02 a 28/02)
    m(conta, date(2026, 2, 25), "a", "200.00", 20000, 400, Decimal(20), Decimal(800))
    db.commit()
    return factory.login(u), c, conta


def test_resumo_bate_com_fixture(dados) -> None:
    cli, c, _ = dados
    r = cli.get(f"/clientes/{c.id}/metricas/resumo?inicio=2026-03-01&fim=2026-03-08").json()
    a = r["atual"]
    assert Decimal(a["investimento"]) == Decimal("300.00")  # nível anúncio excluído
    assert a["impressoes"] == 30000 and a["cliques"] == 300
    assert Decimal(a["conversoes"]) == 15 and Decimal(a["valor_conversoes"]) == 600
    assert Decimal(a["ctr"]) == 1 and Decimal(a["cpc"]) == 1 and Decimal(a["cpm"]) == 10
    assert Decimal(a["cpa"]) == 20 and Decimal(a["roas"]) == 2
    assert r["periodo_anterior"] == {"inicio": "2026-02-21", "fim": "2026-02-28"}
    assert Decimal(r["variacao_percentual"]["investimento"]) == Decimal("50.00")
    assert r["moedas"] == ["BRL"]


def test_filtros_afetam_todas_as_consultas(dados) -> None:
    cli, c, conta = dados
    q = "inicio=2026-03-01&fim=2026-03-08&plataforma=google_ads"
    resumo = cli.get(f"/clientes/{c.id}/metricas/resumo?{q}").json()["atual"]
    serie = cli.get(f"/clientes/{c.id}/metricas/serie?{q}").json()["pontos"]
    camps = cli.get(f"/clientes/{c.id}/campanhas?{q}").json()["items"]
    assert Decimal(resumo["investimento"]) == 150
    assert sum(Decimal(p["kpis"]["investimento"]) for p in serie) == 150
    assert [x["campanha_externa_id"] for x in camps] == ["g"]
    assert resumo["ctr"] == "0.0000" and resumo["cpc"] is None  # 0 cliques: CPC ausente
    assert resumo["conversoes"] is None and resumo["roas"] is None
    r = cli.get(
        f"/clientes/{c.id}/metricas/resumo?inicio=2026-03-01&fim=2026-03-08"
        f"&conta_anuncio_id={conta.id}"
    ).json()["atual"]
    assert Decimal(r["investimento"]) == 150


def test_serie_por_granularidade(dados) -> None:
    cli, c, _ = dados
    base = f"/clientes/{c.id}/metricas/serie?inicio=2026-03-01&fim=2026-03-08"
    dia = cli.get(f"{base}&granularidade=dia").json()["pontos"]
    assert [p["periodo"] for p in dia] == ["2026-03-01", "2026-03-02", "2026-03-08"]
    semana = cli.get(f"{base}&granularidade=semana").json()["pontos"]
    # semanas ISO (segunda-feira): 23/02 (01/03 é domingo), 02/03
    assert [p["periodo"] for p in semana] == ["2026-02-23", "2026-03-02"]
    mes = cli.get(f"{base}&granularidade=mes&comparar=true").json()
    assert [p["periodo"] for p in mes["pontos"]] == ["2026-03-01"]
    assert mes["comparacao"][0]["periodo"] == "2026-02-01"


def test_campanhas_ordenaveis(dados) -> None:
    cli, c, _ = dados
    base = f"/clientes/{c.id}/campanhas?inicio=2026-03-01&fim=2026-03-08"
    desc = cli.get(f"{base}&ordenar_por=investimento&ordem=desc").json()["items"]
    # empate em investimento é desempatado pelo id externo (ordem estável)
    assert [(x["campanha_externa_id"], x["kpis"]["investimento"]) for x in desc] == [
        ("a", "150.00"),
        ("g", "150.00"),
    ]
    asc = cli.get(f"{base}&ordenar_por=cliques&ordem=asc").json()["items"]
    assert [x["campanha_externa_id"] for x in asc] == ["g", "a"]


def test_conta_sem_dados_vazio_e_sem_comparativo(factory) -> None:
    u = factory.usuario("analista")
    c = factory.cliente(membros=(u,))
    cli = factory.login(u)
    r = cli.get(f"/clientes/{c.id}/metricas/resumo").json()
    assert r["integracoes_conectadas"] == 0 and r["anterior"] is None
    assert all(v is None for v in r["variacao_percentual"].values())
    assert r["atual"]["ctr"] is None
    assert cli.get(f"/clientes/{c.id}/metricas/serie").json()["pontos"] == []
    assert cli.get(f"/clientes/{c.id}/campanhas").json()["items"] == []


def test_carteira_alheia_inacessivel(dados, factory) -> None:
    _, c, _ = dados
    outro = factory.login(factory.usuario("analista"))
    for path in ("metricas/resumo", "metricas/serie", "campanhas"):
        assert outro.get(f"/clientes/{c.id}/{path}").status_code == 404


def test_periodo_invalido(dados) -> None:
    cli, c, _ = dados
    r = cli.get(f"/clientes/{c.id}/metricas/resumo?inicio=2026-03-08&fim=2026-03-01")
    assert r.status_code == 422
