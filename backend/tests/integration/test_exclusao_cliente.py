"""Exclusão definitiva de cliente pela tela de Clientes (somente admin)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.core.crypto import store_secret
from app.models import (
    Auditoria,
    Cliente,
    ContaAnuncio,
    CredencialIntegracao,
    Dashboard,
    Integracao,
    MetricaDiaria,
    Relatorio,
    RelatorioExecucao,
    UsuarioCliente,
)
from app.services import relatorios, storage


def _conta(db, modelo) -> int:  # type: ignore[no-untyped-def]
    return db.scalar(select(func.count()).select_from(modelo)) or 0


def test_admin_exclui_cliente_e_tudo_que_pertence_a_ele(factory, db, fila) -> None:
    admin_u = factory.usuario("admin")
    analista = factory.usuario("analista")
    c = factory.cliente("Padaria Sol", membros=(analista,))
    outro = factory.cliente("Mercado Lua", membros=(analista,))
    integ = Integracao(cliente_id=c.id, plataforma="meta_ads", status="conectada")
    db.add(integ)
    db.flush()
    integ.referencia_credencial = store_secret(db, {"access_token": "x"}, integracao_id=integ.id)
    conta = ContaAnuncio(integracao_id=integ.id, conta_externa_id="1", nome="Meta")
    db.add(conta)
    db.flush()
    db.add(
        MetricaDiaria(
            conta_anuncio_id=conta.id,
            data=date.today(),
            nivel="campanha",
            entidade_externa_id="c1",
            investimento=Decimal("10"),
        )
    )
    db.commit()

    cli = factory.login(analista)
    assert cli.post("/dashboards", json={"cliente_id": str(c.id), "nome": "D"}).status_code == 201
    r = cli.post(
        "/relatorios",
        json={
            "cliente_id": str(c.id),
            "titulo": "Mensal",
            "configuracao": {"template": "visao_executiva", "graficos": ["tabela_campanhas"]},
        },
    )
    assert r.status_code == 201, r.text
    job = cli.post(f"/relatorios/{r.json()['id']}/gerar").json()["job_id"]
    assert relatorios.executar(job) == "concluido"
    ref = db.scalar(select(RelatorioExecucao.arquivo_referencia))
    assert ref and storage.ler(ref).startswith(b"%PDF")

    cid, outro_id = c.id, outro.id
    admin = factory.login(admin_u)
    assert admin.delete(f"/clientes/{cid}").status_code == 204

    db.expire_all()
    assert db.get(Cliente, cid) is None
    assert db.get(Cliente, outro_id) is not None  # só o cliente escolhido
    for modelo in (
        Integracao,
        ContaAnuncio,
        MetricaDiaria,
        CredencialIntegracao,
        Dashboard,
        Relatorio,
        RelatorioExecucao,
    ):
        assert _conta(db, modelo) == 0, modelo.__name__
    assert db.scalars(select(UsuarioCliente.cliente_id)).all() == [outro_id]
    assert admin.get(f"/clientes/{cid}").status_code == 404
    try:
        storage.ler(ref)
        raise AssertionError("PDF deveria ter sido removido")
    except storage.StorageError:
        pass
    log = db.scalar(select(Auditoria).where(Auditoria.acao == "excluir"))
    assert log is not None and log.entidade == "cliente" and log.metadados["nome"] == "Padaria Sol"
    assert log.metadados["integracoes"] == 1 and log.metadados["relatorios"] == 1


def test_somente_admin_exclui_cliente(factory) -> None:
    gestor = factory.usuario("gestor")
    c = factory.cliente("Padaria Sol", membros=(gestor,))
    assert factory.login(gestor).delete(f"/clientes/{c.id}").status_code == 403
    admin = factory.login(factory.usuario("admin"))
    assert admin.get(f"/clientes/{c.id}").status_code == 200
    # cliente arquivado também pode ser excluído
    assert admin.post(f"/clientes/{c.id}/arquivar").status_code == 200
    assert admin.delete(f"/clientes/{c.id}").status_code == 204
    assert admin.delete(f"/clientes/{c.id}").status_code == 404
