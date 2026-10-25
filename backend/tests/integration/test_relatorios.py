"""SPEC-05: relatórios, geração assíncrona de PDF, histórico e download privado."""

from __future__ import annotations

import re
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import ContaAnuncio, Integracao, MetricaDiaria, RelatorioExecucao
from app.services import pdf, relatorios
from app.services.relatorios import utcnow

HOJE = date.today()


@pytest.fixture
def cenario(factory, db):  # type: ignore[no-untyped-def]
    analista = factory.usuario("analista")
    vis = factory.usuario("visualizador")
    c = factory.cliente("Padaria Sol", membros=(analista, vis))
    integ = Integracao(cliente_id=c.id, plataforma="meta_ads", status="conectada")
    db.add(integ)
    db.flush()
    conta = ContaAnuncio(
        integracao_id=integ.id, conta_externa_id="1", nome="Meta", ultima_sincronizacao_em=utcnow()
    )
    db.add(conta)
    db.flush()
    for i in range(10):
        db.add(
            MetricaDiaria(
                conta_anuncio_id=conta.id,
                data=HOJE - timedelta(days=i),
                nivel="campanha",
                entidade_externa_id=f"c{i % 3}",
                campanha_externa_id=f"c{i % 3}",
                campanha_nome=f"Campanha com nome longo {i % 3} " * 3,
                investimento=Decimal("10.50"),
                impressoes=1000,
                cliques=40,
                conversoes=Decimal(2),
                valor_conversoes=Decimal(60),
            )
        )
    db.commit()
    cli = factory.login(analista)
    r = cli.post(
        "/relatorios",
        json={
            "cliente_id": str(c.id),
            "titulo": "Mensal",
            "configuracao": {
                "template": "visao_executiva",
                "comentarios": "Bom mês.\n\nSegue.",
                "graficos": ["serie_investimento", "tabela_campanhas"],
            },
        },
    )
    assert r.status_code == 201, r.text
    return cli, factory.login(vis), c, r.json()["id"]


def _gerar(cli, rid, fila, key=None):  # type: ignore[no-untyped-def]
    headers = {"Idempotency-Key": key} if key else {}
    r = cli.post(f"/relatorios/{rid}/gerar", headers=headers)
    assert r.status_code == 202, r.text
    return r.json()


def test_crud_e_templates(cenario) -> None:
    cli, _, c, rid = cenario
    r = cli.get(f"/relatorios/{rid}").json()
    assert r["configuracao"]["template"] == "visao_executiva"
    assert r["configuracao"]["periodo"]["tipo"] == "ultimos_30_dias"
    r = cli.patch(
        f"/relatorios/{rid}",
        json={
            "configuracao": {
                "template": "performance_campanhas",
                "periodo": {"tipo": "personalizado", "inicio": "2026-01-10", "fim": "2026-01-01"},
            }
        },
    )
    assert r.status_code == 422  # período invertido
    r = cli.patch(
        f"/relatorios/{rid}",
        json={"titulo": "Campanhas", "configuracao": {"template": "performance_campanhas"}},
    )
    assert r.json()["titulo"] == "Campanhas"
    assert cli.get(f"/relatorios?cliente_id={c.id}").json()["total"] == 1
    assert cli.delete(f"/relatorios/{rid}").status_code == 204
    assert cli.get(f"/relatorios/{rid}").status_code == 404
    assert cli.get("/relatorios").json()["total"] == 0


def test_geracao_assincrona_pdf_a4_e_snapshot(cenario, fila, db) -> None:
    cli, _, c, rid = cenario
    aceito = _gerar(cli, rid, fila)
    assert aceito["status"] == "pendente" and aceito["status_url"].endswith("/execucoes")
    assert fila.relatorio == [(uuid.UUID(aceito["job_id"]), None)]
    assert relatorios.executar(aceito["job_id"]) == "concluido"
    execs = cli.get(f"/relatorios/{rid}/execucoes").json()["items"]
    ex = execs[0]
    assert ex["status"] == "concluido" and ex["progresso"] == 100
    assert set(ex["snapshot"]) == {"periodo", "filtros", "horario_corte", "ultima_coleta_em"}
    r = cli.get(ex["download_url"].removeprefix("/api/v1"))
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert re.search(rb"/MediaBox \[ ?0 0 595\.27\d* 841\.88\d* ?\]", r.content)  # A4
    assert "no-store" in r.headers["cache-control"]
    # números do snapshot = dashboard no mesmo período
    snap = db.get(RelatorioExecucao, ex["id"]).snapshot
    p = snap["periodo"]
    dash = cli.get(f"/clientes/{c.id}/metricas/resumo?inicio={p['inicio']}&fim={p['fim']}")
    assert snap["dados"]["resumo"]["atual"] == dash.json()["atual"]
    assert "/var/" not in str(ex) and "local:" not in str(ex)  # sem caminho interno


def test_idempotencia_e_falha_recuperavel(cenario, fila, monkeypatch) -> None:
    cli, _, _, rid = cenario
    a = _gerar(cli, rid, fila, key="chave-abc-123")
    b = _gerar(cli, rid, fila, key="chave-abc-123")
    assert a["job_id"] == b["job_id"] and len(fila.relatorio) == 1
    monkeypatch.setattr(pdf, "renderizar", lambda s: (_ for _ in ()).throw(RuntimeError("x")))
    assert relatorios.executar(a["job_id"]) == "erro"
    ex = cli.get(f"/relatorios/{rid}/execucoes").json()["items"][0]
    assert ex["status"] == "erro" and "Gere novamente" in ex["erro"] and ex["download_url"] is None
    monkeypatch.undo()
    fila.relatorio.clear()
    _gerar(cli, rid, fila, key="chave-abc-123")  # mesma chave: reprocessa o mesmo snapshot
    assert len(fila.relatorio) == 1
    assert relatorios.executar(a["job_id"]) == "concluido"
    assert _gerar(cli, rid, fila)["job_id"] != a["job_id"]  # sem chave: nova execução


def test_permissoes_e_isolamento(cenario, fila, factory) -> None:
    cli, vis, c, rid = cenario
    ex_id = _gerar(cli, rid, fila)["job_id"]
    relatorios.executar(ex_id)
    url = f"/relatorios/execucoes/{ex_id}/download"
    assert vis.get(f"/relatorios/{rid}").status_code == 200
    assert vis.get(url).status_code == 200  # leitura permitida ao visualizador
    assert vis.post(f"/relatorios/{rid}/gerar").status_code == 403
    assert (
        vis.post("/relatorios", json={"cliente_id": str(c.id), "titulo": "X Y"}).status_code == 403
    )
    outro = factory.login(factory.usuario("gestor"))
    assert outro.get(url).status_code == 404
    assert outro.get(f"/relatorios/{rid}").status_code == 404
    assert outro.get(f"/relatorios/{rid}/execucoes").status_code == 404
    assert outro.post(f"/relatorios/{rid}/gerar").status_code == 404


def test_historico_preservado_apos_arquivar_cliente(cenario, fila, factory) -> None:
    cli, _, c, rid = cenario
    ex_id = _gerar(cli, rid, fila)["job_id"]
    relatorios.executar(ex_id)
    admin = factory.login(factory.usuario("admin"))
    assert admin.post(f"/clientes/{c.id}/arquivar").status_code == 200
    assert cli.get(f"/relatorios/{rid}/execucoes").json()["total"] == 1
    assert cli.get(f"/relatorios/execucoes/{ex_id}/download").status_code == 200
    assert cli.post(f"/relatorios/{rid}/gerar").status_code == 409


def test_retencao_remove_arquivo_mas_mantem_registro(cenario, fila, db) -> None:
    cli, _, _, rid = cenario
    ex_id = _gerar(cli, rid, fila)["job_id"]
    relatorios.executar(ex_id)
    ex = db.get(RelatorioExecucao, uuid.UUID(ex_id))
    ex.expira_em = utcnow() - timedelta(days=1)
    db.commit()
    assert relatorios.limpar_expirados(db) == 1
    r = cli.get(f"/relatorios/execucoes/{ex_id}/download")
    assert r.status_code == 404 and r.json()["error"]["code"] == "GONE"
    assert (
        db.scalar(select(RelatorioExecucao.status).where(RelatorioExecucao.id == ex.id))
        == "concluido"
    )


def test_pdf_tabela_longa_quebra_sem_cortar() -> None:
    camps = [
        {
            "plataforma": "meta_ads",
            "campanha_externa_id": str(i),
            "campanha_nome": f"Campanha {i} " + "x" * 120,
            "kpis": {
                "investimento": "10",
                "impressoes": 100,
                "cliques": 1,
                "ctr": "1",
                "cpc": "10",
                "conversoes": None,
                "cpa": None,
                "roas": None,
            },
        }
        for i in range(150)
    ]
    kz = dict.fromkeys(
        [
            "investimento",
            "impressoes",
            "cliques",
            "conversoes",
            "valor_conversoes",
            "ctr",
            "cpc",
            "cpm",
            "cpa",
            "roas",
        ]
    )
    snap = {
        "titulo": "T",
        "cliente": "C",
        "periodo": {"inicio": "2026-01-01", "fim": "2026-01-31"},
        "horario_corte": "2026-02-01T00:00:00+00:00",
        "ultima_coleta_em": None,
        "configuracao": {
            "template": "performance_campanhas",
            "kpis": list(kz),
            "graficos": ["tabela_campanhas"],
            "comentarios": None,
        },
        "dados": {
            "resumo": {"atual": kz, "anterior": None, "variacao_percentual": kz, "moedas": ["BRL"]},
            "serie": None,
            "campanhas": camps,
        },
    }
    out = pdf.renderizar(snap)
    assert out.startswith(b"%PDF")
    paginas = len(re.findall(rb"/Type /Page[^s]", out))
    assert paginas >= 3  # 150 linhas repartidas em várias páginas, cabeçalho repetido
