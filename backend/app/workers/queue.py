"""Envio de tarefas ao Celery e semáforo de concorrência por provedor."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import lru_cache
from typing import cast

import redis

from app.core.config import get_settings

# Tarefas assíncronas conhecidas (nome Celery).
SYNC = "v4.sync"
RELATORIO = "v4.relatorio"

Override = Callable[[str, uuid.UUID, float | None], None]
# Em testes, substituído por uma função que registra/executa a tarefa localmente.
_override: Override | None = None


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(
        get_settings().redis_url, socket_connect_timeout=2, socket_timeout=10
    )


def enqueue(tarefa: str, objeto_id: uuid.UUID, delay_seconds: float | None = None) -> None:
    if _override is not None:
        _override(tarefa, objeto_id, delay_seconds)
        return
    from app.workers.celery_app import celery_app

    celery_app.send_task(tarefa, args=[str(objeto_id)], countdown=delay_seconds or None)


def enqueue_job(job_id: uuid.UUID, delay_seconds: float | None = None) -> None:
    enqueue(SYNC, job_id, delay_seconds)


def set_enqueue_override(fn: Override | None) -> None:
    global _override
    _override = fn


def modo_sincrono() -> bool:
    return _override is not None


class ProviderSlot:
    """Semáforo distribuído simples: limita jobs simultâneos por provedor."""

    TTL = 3600

    def __init__(self, plataforma: str) -> None:
        self.key = f"v4:sync:slots:{plataforma}"
        self.limit = get_settings().sync_max_concurrency_per_provider
        self.acquired = False

    def __enter__(self) -> bool:
        if modo_sincrono():
            self.acquired = True
            return True
        r = get_redis()
        n = cast(int, r.incr(self.key))
        r.expire(self.key, self.TTL)
        if n > self.limit:
            r.decr(self.key)
            return False
        self.acquired = True
        return True

    def __exit__(self, *exc: object) -> None:
        if self.acquired and not modo_sincrono():
            get_redis().decr(self.key)
