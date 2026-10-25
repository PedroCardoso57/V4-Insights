"""Alertas operacionais (SPEC-07) enviados a um webhook, com deduplicação no Redis."""

from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.sanitize import sanitize
from app.models import Cliente, ContaAnuncio, Integracao, StatusIntegracao, SyncJob
from app.workers.queue import get_redis

log = logging.getLogger(__name__)
SILENCIO = timedelta(hours=6)  # não repete o mesmo alerta antes disso


def enviar(chave: str, mensagem: str) -> bool:
    """Envia o alerta (uma vez por janela de silêncio). Retorna True se enviou."""
    s = get_settings()
    texto = sanitize(f"[V4 Insights · {s.environment}] {mensagem}", 1500)
    log.warning("alerta: %s", texto)
    try:
        if not get_redis().set(
            f"v4:alerta:{chave}", "1", nx=True, ex=int(SILENCIO.total_seconds())
        ):
            return False
    except Exception as exc:  # sem Redis não há deduplicação, mas o alerta ainda sai
        log.debug("deduplicação indisponível: %s", exc.__class__.__name__)
    if not s.alert_webhook_url:
        return False
    try:
        httpx.post(s.alert_webhook_url, json={"text": texto}, timeout=10).raise_for_status()
        return True
    except httpx.HTTPError as exc:
        log.error("falha ao enviar alerta: %s", exc.__class__.__name__)
        return False


def sync_com_erro_persistente(db: Session) -> list[str]:
    """Contas cujos últimos N jobs falharam, e integrações que exigem reconexão."""
    n = get_settings().alert_sync_falhas_consecutivas
    problemas: list[str] = []
    contas = db.execute(
        select(ContaAnuncio, Integracao.plataforma, Cliente.nome)
        .join(Integracao, Integracao.id == ContaAnuncio.integracao_id)
        .join(Cliente, Cliente.id == Integracao.cliente_id)
        .where(ContaAnuncio.ativa.is_(True), Integracao.status == StatusIntegracao.conectada.value)
    ).all()
    for conta, plataforma, cliente in contas:
        ultimos = db.scalars(
            select(SyncJob.status)
            .where(SyncJob.conta_anuncio_id == conta.id, SyncJob.status.in_(["sucesso", "erro"]))
            .order_by(SyncJob.criado_em.desc())
            .limit(n)
        ).all()
        if len(ultimos) == n and all(st == "erro" for st in ultimos):
            problemas.append(
                f"{cliente} · {plataforma} · conta {conta.conta_externa_id}: "
                f"{n} sincronizações seguidas com erro"
            )
    for nome, plataforma in db.execute(
        select(Cliente.nome, Integracao.plataforma)
        .join(Cliente)
        .where(Integracao.status == StatusIntegracao.erro.value)
    ):
        problemas.append(f"{nome} · {plataforma}: integração requer reconexão")
    return problemas


def verificar(db: Session) -> int:
    """Executado periodicamente pelo beat. Retorna quantos alertas foram disparados."""
    enviados = 0
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return int(enviar("readiness-db", "Banco de dados indisponível para o worker."))
    for p in sync_com_erro_persistente(db):
        enviados += enviar(f"sync:{p}", f"Erro persistente de sincronização — {p}")
    uso = shutil.disk_usage(get_settings().reports_storage_dir)
    pct = 100 * uso.used / uso.total
    if pct >= 85:
        enviados += enviar("disco", f"Armazenamento em {pct:.0f}% no volume de relatórios.")
    pend = db.scalar(
        select(SyncJob.criado_em)
        .where(SyncJob.status == "pendente")
        .order_by(SyncJob.criado_em)
        .limit(1)
    )
    if pend and datetime.now(UTC) - pend > timedelta(hours=2):
        enviados += enviar(
            "fila", "Há jobs de sincronização pendentes há mais de 2h (worker parado?)."
        )
    return enviados
