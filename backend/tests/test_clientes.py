from __future__ import annotations

from sqlalchemy import select

from app.models import Auditoria, UsuarioCliente


def test_crud_busca_e_normalizacao(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    r = admin.post("/clientes", json={"nome": "  Padaria Sol ", "documento": "12.345.678/0001-90"})
    assert r.status_code == 201
    c = r.json()
    assert c["nome"] == "Padaria Sol" and c["documento"] == "12345678000190"
    assert admin.post("/clientes", json={"nome": "X", "documento": "123"}).status_code == 422
    assert admin.post("/clientes", json={"nome": "   "}).status_code == 422
    assert admin.post("/clientes", json={"nome": "a" * 161}).status_code == 422
    r = admin.patch(f"/clientes/{c['id']}", json={"nome_fantasia": "Sol"})
    assert r.status_code == 200 and r.json()["nome_fantasia"] == "Sol"
    assert admin.patch(f"/clientes/{c['id']}", json={"nome": None}).status_code == 422
    admin.post("/clientes", json={"nome": "Mercado Lua"})
    r = admin.get("/clientes?search=sol")
    assert [x["nome"] for x in r.json()["items"]] == ["Padaria Sol"]


def test_paginacao_estavel(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    for i in range(7):
        admin.post("/clientes", json={"nome": "Mesmo Nome"})  # empate na ordenação
    ids = []
    for page in (1, 2, 3):
        r = admin.get(f"/clientes?page={page}&page_size=3").json()
        assert r["total"] == 7
        ids += [x["id"] for x in r["items"]]
    assert len(ids) == 7 and len(set(ids)) == 7
    desc = admin.get("/clientes?order_by=nome&order=desc&page_size=100").json()["items"]
    assert [x["id"] for x in desc] == sorted(ids, reverse=True)


def test_arquivar_preserva_e_filtra(factory, db) -> None:
    admin = factory.login(factory.usuario("admin"))
    c = admin.post("/clientes", json={"nome": "Arquivável"}).json()
    r = admin.post(f"/clientes/{c['id']}/arquivar")
    assert r.status_code == 200 and r.json()["status"] == "arquivado"
    assert r.json()["arquivado_em"] is not None
    assert admin.get(f"/clientes/{c['id']}").status_code == 200
    assert admin.get("/clientes?status=ativo").json()["total"] == 0
    assert admin.get("/clientes?status=arquivado").json()["total"] == 1
    assert admin.patch(f"/clientes/{c['id']}", json={"nome": "Outro"}).status_code == 409
    acoes = db.scalars(select(Auditoria.acao).where(Auditoria.entidade == "cliente")).all()
    assert set(acoes) == {"criar", "arquivar"}


def test_isolamento_de_carteiras(factory) -> None:
    ua, ub = factory.usuario("analista"), factory.usuario("analista")
    ca = factory.cliente("Cliente A", membros=(ua,))
    cb = factory.cliente("Cliente B", membros=(ub,))
    a, b = factory.login(ua), factory.login(ub)
    assert [x["id"] for x in a.get("/clientes").json()["items"]] == [str(ca.id)]
    assert a.get(f"/clientes/{cb.id}").status_code == 404
    assert b.get(f"/clientes/{ca.id}").status_code == 404
    assert a.get(f"/clientes/{cb.id}/usuarios").status_code == 404


def test_permissoes_de_gestao(factory, db) -> None:
    gestor_u = factory.usuario("gestor")
    g = factory.login(gestor_u)
    r = g.post("/clientes", json={"nome": "Do Gestor"})
    assert r.status_code == 201
    cid = r.json()["id"]
    # gestor que cria entra automaticamente na carteira
    assert db.get(UsuarioCliente, (gestor_u.id, r.json()["id"])) is not None
    assert g.get(f"/clientes/{cid}/usuarios").json()[0]["id"] == str(gestor_u.id)
    for papel in ("analista", "visualizador"):
        u = factory.usuario(papel)
        c = factory.cliente(membros=(u,))
        cli = factory.login(u)
        assert cli.post("/clientes", json={"nome": "Nope"}).status_code == 403
        assert cli.patch(f"/clientes/{c.id}", json={"nome": "Nope"}).status_code == 403
        assert cli.post(f"/clientes/{c.id}/arquivar").status_code == 403


def test_auditoria_filtrada_por_carteira(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    gestor_u = factory.usuario("gestor")
    meu = admin.post("/clientes", json={"nome": "Meu"}).json()
    admin.post("/clientes", json={"nome": "Alheio"})
    admin.put(f"/usuarios/{gestor_u.id}/clientes/{meu['id']}")
    g = factory.login(gestor_u)
    itens = g.get("/auditoria").json()["items"]
    assert itens and all(i["cliente_id"] == meu["id"] for i in itens)
    assert admin.get("/auditoria").json()["total"] > len(itens)
    assert factory.login(factory.usuario("analista")).get("/auditoria").status_code == 403
