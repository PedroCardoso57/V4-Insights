"""Tarefas Celery. A lógica fica em app.services; aqui só há a casca de execução."""

from __future__ import annotations

import logging

from app.db.session import get_sessionmaker
from app.services import relatorios, sync
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="v4.sync")
def executar_sync(job_id: str) -> str:
    return sync.run_job(job_id)


@celery_app.task(name="v4.relatorio")
def gerar_relatorio(execucao_id: str) -> str:
    return relatorios.executar(execucao_id)


@celery_app.task(name="v4.agendador")
def agendador() -> None:
    db = get_sessionmaker()()
    try:
        criados = sync.agendar_incrementais(db)
        recuperados = sync.reenfileirar_atrasados(db)
        recuperados += relatorios.reenfileirar_atrasados(db)
        if criados or recuperados:
            log.info("agendador: %s incrementais, %s reenfileirados", criados, recuperados)
    finally:
        db.close()


@celery_app.task(name="v4.limpar_relatorios")
def limpar_relatorios() -> None:
    db = get_sessionmaker()()
    try:
        n = relatorios.limpar_expirados(db)
        if n:
            log.info("relatórios expirados removidos: %s", n)
    finally:
        db.close()
