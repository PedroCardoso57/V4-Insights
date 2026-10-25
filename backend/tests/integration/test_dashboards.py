from __future__ import annotations


def test_crud_de_dashboard_e_widgets(factory) -> None:
    u = factory.usuario("analista")
    c = factory.cliente(membros=(u,))
    cli = factory.login(u)
    r = cli.post(
        "/dashboards",
        json={"cliente_id": str(c.id), "nome": "Visão geral", "filtros": {"granularidade": "dia"}},
    )
    assert r.status_code == 201
    did = r.json()["id"]
    w = cli.post(
        f"/dashboards/{did}/widgets",
        json={"tipo": "kpi", "titulo": "Investimento", "config": {"kpi": "investimento"}},
    )
    assert w.status_code == 201
    assert (
        cli.post(f"/dashboards/{did}/widgets", json={"tipo": "pizza", "titulo": "x"}).status_code
        == 422
    )
    r = cli.patch(
        f"/dashboards/{did}",
        json={
            "nome": "Renomeado",
            "widgets": [
                {"tipo": "serie", "titulo": "Cliques", "config": {"kpi": "cliques"}},
                {"tipo": "tabela_campanhas", "titulo": "Campanhas"},
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["nome"] == "Renomeado"
    assert [x["tipo"] for x in body["widgets"]] == ["serie", "tabela_campanhas"]
    assert [d["id"] for d in cli.get(f"/dashboards?cliente_id={c.id}").json()["items"]] == [did]
    assert cli.delete(f"/dashboards/{did}").status_code == 204
    assert cli.get(f"/dashboards/{did}").status_code == 404


def test_visualizador_somente_leitura(factory) -> None:
    autor = factory.usuario("analista")
    vis = factory.usuario("visualizador")
    c = factory.cliente(membros=(autor, vis))
    did = (
        factory.login(autor)
        .post("/dashboards", json={"cliente_id": str(c.id), "nome": "D"})
        .json()["id"]
    )
    v = factory.login(vis)
    assert v.get(f"/dashboards/{did}").status_code == 200
    assert v.post("/dashboards", json={"cliente_id": str(c.id), "nome": "X"}).status_code == 403
    assert v.patch(f"/dashboards/{did}", json={"nome": "X"}).status_code == 403
    assert v.delete(f"/dashboards/{did}").status_code == 403


def test_dashboard_de_outra_carteira(factory) -> None:
    a = factory.usuario("analista")
    c = factory.cliente(membros=(a,))
    did = (
        factory.login(a)
        .post("/dashboards", json={"cliente_id": str(c.id), "nome": "D"})
        .json()["id"]
    )
    outro = factory.login(factory.usuario("analista"))
    assert outro.get(f"/dashboards/{did}").status_code == 404
    assert outro.get("/dashboards").json()["items"] == []
    assert outro.post("/dashboards", json={"cliente_id": str(c.id), "nome": "X"}).status_code == 404
