"""Aplicação Celery (broker Redis).

    celery -A app.workers.celery_app worker -B --loglevel INFO

`-B` embute o agendador (beat): mantenha apenas UMA réplica com -B, ou rode o beat
separadamente (`celery -A app.workers.celery_app beat`).
"""

from __future__ import annotations

from celery import Celery
from celery.signals import setup_logging

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("v4_insights", broker=settings.redis_url, include=["app.workers.tasks"])
celery_app.conf.update(
    task_ignore_result=True,
    task_acks_late=True,  # job só sai da fila quando concluído (worker caído → reentrega)
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="v4",
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 4 * 3600},
    timezone="UTC",
    beat_schedule_filename="/tmp/celerybeat-schedule",  # noqa: S108
    beat_schedule={
        "agendar-sincronizacoes": {"task": "v4.agendador", "schedule": 300.0},
        "limpar-relatorios-expirados": {"task": "v4.limpar_relatorios", "schedule": 3600.0},
    },
)


@setup_logging.connect
def _logging(**_: object) -> None:
    # Mantém o formato JSON sanitizado da aplicação nos logs do worker.
    from app.core.logging import configure_logging

    configure_logging(settings.log_level)
