"""Criação e execução de jobs de sincronização de métricas."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import load_secret, store_secret
from app.core.sanitize import sanitize
from app.db.session import get_sessionmaker
from app.integrations.base import (
    MetricRow,
    PermissionProviderError,
    ProviderError,
    aplicar_mapeamento,
    backoff_seconds,
)
from app.integrations.registry import get_provider
from app.models import (
    Cliente,
    ContaAnuncio,
    Integracao,
    MetricaDiaria,
    StatusCliente,
    StatusIntegracao,
    StatusJob,
    SyncJob,
    TipoJob,
)
from app.workers.queue import ProviderSlot, enqueue_job

log = logging.getLogger(__name__)

NIVEIS_SYNC = ("campanha",)
LOOKBACK_DIAS = 3  # reprocessa dias recentes: provedores ajustam métricas tardiamente
BATCH = 500


def utcnow() -> datetime:
    return datetime.now(UTC)


def hoje_conta(conta: ContaAnuncio) -> date:
    try:
        tz = ZoneInfo(conta.fuso_horario) if conta.fuso_horario else UTC
    except Exception:  # fuso desconhecido
        tz = UTC
    return datetime.now(tz).date()


def _bucket(tipo: TipoJob) -> str:
    """Janela de idempotência: o mesmo pedido no mesmo período não gera job novo."""
    t = utcnow()
    if tipo is TipoJob.incremental:
        h = get_settings().sync_interval_hours
        return t.strftime("%Y%m%d") + f"-{t.hour // h}"
    if tipo is TipoJob.manual:
        return t.strftime("%Y%m%d%H") + f"-{t.minute // 5}"
    return "unico"


def criar_job(
    db: Session,
    conta: ContaAnuncio,
    tipo: TipoJob,
    inicio: date,
    fim: date,
    criado_por: uuid.UUID | None = None,
) -> tuple[SyncJob, bool]:
    """Cria o job se ainda não existir com a mesma chave idempotente. Retorna (job, criado)."""
    key = f"{conta.id}:{tipo.value}:{inicio.isoformat()}:{fim.isoformat()}:{_bucket(tipo)}"
    stmt = (
        pg_insert(SyncJob)
        .values(
            id=uuid.uuid4(),
            integracao_id=conta.integracao_id,
            conta_anuncio_id=conta.id,
            tipo=tipo.value,
            status=StatusJob.pendente.value,
            idempotency_key=key,
            periodo_inicio=inicio,
            periodo_fim=fim,
            criado_por=criado_por,
        )
        .on_conflict_do_nothing(constraint="uq_sync_jobs_idem")
        .returning(SyncJob.id)
    )
    new_id = db.execute(stmt).scalar()
    job = db.scalar(
        select(SyncJob).where(
            SyncJob.integracao_id == conta.integracao_id, SyncJob.idempotency_key == key
        )
    )
    assert job is not None
    return job, new_id is not None


def agendar(db: Session, job: SyncJob, criado: bool) -> None:
    db.commit()
    if criado:
        enqueue_job(job.id)


def janela_incremental(conta: ContaAnuncio) -> tuple[date, date]:
    fim = hoje_conta(conta)
    if conta.dados_ate:
        inicio = min(conta.dados_ate, fim) - timedelta(days=LOOKBACK_DIAS)
    else:
        inicio = fim - timedelta(days=conta.carga_historica_dias)
    return inicio, fim


def cancelar_pendentes(db: Session, integracao_id: uuid.UUID, motivo: str) -> None:
    db.execute(
        update(SyncJob)
        .where(
            SyncJob.integracao_id == integracao_id,
            SyncJob.status.in_([StatusJob.pendente.value, StatusJob.executando.value]),
        )
        .values(status=StatusJob.cancelado.value, erro_sanitizado=motivo, finalizado_em=utcnow())
    )


# --- Execução -------------------------------------------------------------


def run_job(job_id: str | uuid.UUID) -> str:
    """Entrada do worker. Retorna o status final (útil em testes)."""
    db = get_sessionmaker()()
    try:
        return _run(db, uuid.UUID(str(job_id)))
    finally:
        db.close()


def _run(db: Session, job_id: uuid.UUID) -> str:
    job = db.scalar(select(SyncJob).where(SyncJob.id == job_id).with_for_update(skip_locked=True))
    if job is None or job.status != StatusJob.pendente.value:
        db.rollback()
        return job.status if job else "inexistente"
    conta = db.get(ContaAnuncio, job.conta_anuncio_id)
    integ = db.get(Integracao, job.integracao_id)
    cliente = db.get(Cliente, integ.cliente_id) if integ else None
    if (
        conta is None
        or integ is None
        or integ.status != StatusIntegracao.conectada.value
        or not conta.ativa
        or (cliente is not None and cliente.status == StatusCliente.arquivado.value)
    ):
        job.status = StatusJob.cancelado.value
        job.erro_sanitizado = "integração inativa, revogada ou conta desabilitada"
        job.finalizado_em = utcnow()
        db.commit()
        return job.status

    with ProviderSlot(integ.plataforma) as ok:
        if not ok:
            # Limite de concorrência do provedor atingido: tenta novamente em breve.
            job.proxima_tentativa_em = utcnow() + timedelta(seconds=30)
            db.commit()
            enqueue_job(job.id, 30)
            return job.status
        job.status = StatusJob.executando.value
        job.iniciado_em = utcnow()
        job.tentativa += 1
        db.commit()
        try:
            linhas = _coletar(db, job, conta, integ)
        except ProviderError as exc:
            db.rollback()
            return _falha(db, job.id, exc)
        except Exception as exc:
            db.rollback()
            log.exception("falha inesperada no job %s", job.id)
            return _falha(db, job.id, ProviderError(f"erro interno: {exc.__class__.__name__}"))

    job = db.get(SyncJob, job_id)
    conta = db.get(ContaAnuncio, job.conta_anuncio_id)  # type: ignore[union-attr]
    assert job is not None and conta is not None
    if job.status == StatusJob.cancelado.value:  # revogada durante a coleta
        db.commit()
        return job.status
    job.status = StatusJob.sucesso.value
    job.total_registros = linhas
    job.erro_sanitizado = None
    job.finalizado_em = utcnow()
    conta.ultima_sincronizacao_em = utcnow()
    conta.integracao.ultima_sincronizacao_em = conta.ultima_sincronizacao_em
    conta.integracao.erro_sincronizacao = None
    if conta.dados_ate is None or job.periodo_fim > conta.dados_ate:
        conta.dados_ate = job.periodo_fim
    db.commit()
    return job.status


def _coletar(db: Session, job: SyncJob, conta: ContaAnuncio, integ: Integracao) -> int:
    provider = get_provider(integ.plataforma)
    if not integ.referencia_credencial:
        raise PermissionProviderError("integração sem credencial")
    creds = load_secret(db, integ.referencia_credencial)
    renovadas = provider.ensure_fresh(creds)
    if renovadas is not None:
        store_secret(db, renovadas, integ.referencia_credencial)
        db.commit()
        creds = renovadas
    total = 0
    for nivel in NIVEIS_SYNC:
        lote: list[MetricRow] = []
        for row in provider.fetch_metrics(
            creds,
            conta.conta_externa_id,
            nivel,
            job.periodo_inicio,
            job.periodo_fim,
            conta.mapeamento_conversoes or {},
        ):
            lote.append(row)
            if len(lote) >= BATCH:
                total += _flush(db, job, conta, integ, lote)
                lote = []
        if lote:
            total += _flush(db, job, conta, integ, lote)
    return total


def _flush(
    db: Session, job: SyncJob, conta: ContaAnuncio, integ: Integracao, rows: list[MetricRow]
) -> int:
    # Revogação interrompe a coleta: confere o status antes de gravar cada lote.
    db.refresh(integ)
    if integ.status != StatusIntegracao.conectada.value:
        raise PermissionProviderError("integração revogada ou pausada durante a coleta")
    upsert_metricas(db, conta, rows)
    db.commit()
    return len(rows)


def upsert_metricas(db: Session, conta: ContaAnuncio, rows: list[MetricRow]) -> None:
    """UPSERT idempotente pela chave (conta_anuncio_id, data, nivel, entidade_externa_id)."""
    if not rows:
        return
    mapeamento = conta.mapeamento_conversoes or {}
    # Deduplica dentro do lote (última ocorrência vence) para o ON CONFLICT.
    porchave: dict[tuple[Any, ...], dict[str, Any]] = {}
    for r in rows:
        conv, valor = aplicar_mapeamento(r.conversoes_detalhe, mapeamento)
        porchave[(r.data, r.nivel, r.entidade_externa_id)] = {
            "conta_anuncio_id": conta.id,
            "data": r.data,
            "nivel": r.nivel,
            "entidade_externa_id": r.entidade_externa_id,
            "entidade_nome": r.entidade_nome,
            "campanha_externa_id": r.campanha_externa_id,
            "campanha_nome": r.campanha_nome,
            "conjunto_externo_id": r.conjunto_externo_id,
            "conjunto_nome": r.conjunto_nome,
            "investimento": r.investimento,
            "impressoes": r.impressoes,
            "cliques": r.cliques,
            "conversoes": conv,
            "valor_conversoes": valor,
            "conversoes_detalhe": r.conversoes_detalhe,
            "dados_extras": r.extras,
        }
    stmt = pg_insert(MetricaDiaria).values(list(porchave.values()))
    cols = [
        "entidade_nome",
        "campanha_externa_id",
        "campanha_nome",
        "conjunto_externo_id",
        "conjunto_nome",
        "investimento",
        "impressoes",
        "cliques",
        "conversoes",
        "valor_conversoes",
        "conversoes_detalhe",
        "dados_extras",
    ]
    stmt = stmt.on_conflict_do_update(
        index_elements=["conta_anuncio_id", "data", "nivel", "entidade_externa_id"],
        set_={**{c: stmt.excluded[c] for c in cols}, "sincronizado_em": utcnow()},
    )
    db.execute(stmt)


def recalcular_conversoes(db: Session, conta: ContaAnuncio) -> int:
    """Reaplica o mapeamento de conversões aos dados já coletados da conta."""
    n = 0
    for m in db.scalars(select(MetricaDiaria).where(MetricaDiaria.conta_anuncio_id == conta.id)):
        m.conversoes, m.valor_conversoes = aplicar_mapeamento(
            m.conversoes_detalhe or {}, conta.mapeamento_conversoes or {}
        )
        n += 1
    return n


def _falha(db: Session, job_id: uuid.UUID, exc: ProviderError) -> str:
    settings = get_settings()
    job = db.get(SyncJob, job_id)
    assert job is not None
    integ = db.get(Integracao, job.integracao_id)
    job.erro_sanitizado = sanitize(str(exc))
    if job.status == StatusJob.cancelado.value:
        db.commit()
        return job.status
    if exc.retryable and job.tentativa < settings.sync_max_retries:
        delay = exc.retry_after or backoff_seconds(job.tentativa)
        job.status = StatusJob.pendente.value
        job.proxima_tentativa_em = utcnow() + timedelta(seconds=delay)
        db.commit()
        enqueue_job(job.id, delay)
        return job.status
    job.status = StatusJob.erro.value
    job.finalizado_em = utcnow()
    if (
        isinstance(exc, PermissionProviderError)
        and integ is not None
        and (integ.status == StatusIntegracao.conectada.value)
    ):
        # Erro de permissão não é repetido: a integração passa a exigir reconexão.
        integ.status = StatusIntegracao.erro.value
        integ.erro_sincronizacao = job.erro_sanitizado
    db.commit()
    return job.status


# --- Agendamento ----------------------------------------------------------


def agendar_incrementais(db: Session) -> int:
    """Cria jobs incrementais para contas cuja última sincronização excedeu o intervalo."""
    limite = utcnow() - timedelta(hours=get_settings().sync_interval_hours)
    contas = db.scalars(
        select(ContaAnuncio)
        .join(Integracao, Integracao.id == ContaAnuncio.integracao_id)
        .join(Cliente, Cliente.id == Integracao.cliente_id)
        .where(
            Integracao.status == StatusIntegracao.conectada.value,
            Cliente.status == StatusCliente.ativo.value,
            ContaAnuncio.ativa.is_(True),
            (ContaAnuncio.ultima_sincronizacao_em.is_(None))
            | (ContaAnuncio.ultima_sincronizacao_em < limite),
        )
    ).all()
    n = 0
    for conta in contas:
        em_aberto = db.scalar(
            select(SyncJob.id)
            .where(
                SyncJob.conta_anuncio_id == conta.id,
                SyncJob.status.in_([StatusJob.pendente.value, StatusJob.executando.value]),
            )
            .limit(1)
        )
        if em_aberto:
            continue
        inicio, fim = janela_incremental(conta)
        job, criado = criar_job(db, conta, TipoJob.incremental, inicio, fim)
        agendar(db, job, criado)
        n += int(criado)
    return n


def reenfileirar_atrasados(db: Session) -> int:
    """Recupera jobs pendentes cuja mensagem na fila se perdeu (ex.: Redis reiniciado)."""
    limite = utcnow() - timedelta(minutes=15)
    jobs = db.scalars(
        select(SyncJob).where(
            SyncJob.status == StatusJob.pendente.value,
            ((SyncJob.proxima_tentativa_em.is_(None)) & (SyncJob.criado_em < limite))
            | (SyncJob.proxima_tentativa_em < limite),
        )
    ).all()
    for job in jobs:
        enqueue_job(job.id)
    # Jobs "executando" há mais de 2h foram interrompidos (worker caiu).
    db.execute(
        update(SyncJob)
        .where(
            SyncJob.status == StatusJob.executando.value,
            SyncJob.iniciado_em < utcnow() - timedelta(hours=2),
        )
        .values(
            status=StatusJob.erro.value,
            erro_sanitizado="execução interrompida",
            finalizado_em=utcnow(),
        )
    )
    db.commit()
    return len(jobs)
