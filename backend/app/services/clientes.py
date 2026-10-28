"""Exclusão definitiva de clientes (tela de Clientes, somente admin).

Diferente do arquivamento, apaga o cliente e tudo o que pertence a ele: integrações e
credenciais, contas de anúncio, métricas, jobs, dashboards, relatórios e os PDFs gerados.
A auditoria permanece (cliente_id vira NULL) com o registro da exclusão.
"""

from __future__ import annotations

import uuid

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Cliente,
    ContaAnuncio,
    CredencialIntegracao,
    Dashboard,
    Integracao,
    MetricaDiaria,
    Relatorio,
    RelatorioExecucao,
    SyncJob,
)
from app.services.audit import registrar


def excluir(
    db: Session, cliente: Cliente, *, ator_id: uuid.UUID, request: Request | None = None
) -> list[str]:
    """Apaga o cliente e seus dados. Devolve as referências dos PDFs a remover do storage
    (só depois do commit, para não perder arquivos se a transação falhar)."""
    integracoes = select(Integracao.id).where(Integracao.cliente_id == cliente.id)
    contas = select(ContaAnuncio.id).where(ContaAnuncio.integracao_id.in_(integracoes))
    relatorios = select(Relatorio.id).where(Relatorio.cliente_id == cliente.id)

    pdfs = [
        ref
        for ref in db.scalars(
            select(RelatorioExecucao.arquivo_referencia).where(
                RelatorioExecucao.relatorio_id.in_(relatorios),
                RelatorioExecucao.arquivo_referencia.is_not(None),
            )
        )
        if ref
    ]
    contagem = {
        "integracoes": len(db.scalars(integracoes).all()),
        "relatorios": len(db.scalars(relatorios).all()),
    }

    db.execute(delete(MetricaDiaria).where(MetricaDiaria.conta_anuncio_id.in_(contas)))
    db.execute(delete(SyncJob).where(SyncJob.integracao_id.in_(integracoes)))
    db.execute(delete(ContaAnuncio).where(ContaAnuncio.integracao_id.in_(integracoes)))
    db.execute(
        delete(CredencialIntegracao).where(CredencialIntegracao.integracao_id.in_(integracoes))
    )
    db.execute(delete(Integracao).where(Integracao.cliente_id == cliente.id))
    db.execute(delete(RelatorioExecucao).where(RelatorioExecucao.relatorio_id.in_(relatorios)))
    db.execute(delete(Relatorio).where(Relatorio.cliente_id == cliente.id))
    db.execute(delete(Dashboard).where(Dashboard.cliente_id == cliente.id))

    registrar(
        db,
        usuario_id=ator_id,
        acao="excluir",
        entidade="cliente",
        entidade_id=cliente.id,
        dados={"nome": cliente.nome, **contagem},
        request=request,
    )
    db.execute(delete(Cliente).where(Cliente.id == cliente.id))
    return pdfs
