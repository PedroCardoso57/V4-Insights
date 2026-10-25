"""Fila de jobs (RQ/Redis) e semáforo de concorrência por provedor."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import timedelta
from functools import lru_cache

import redis
from rq import Queue

from app.config import get_settings

QUEUE_NAME = "sync"

# Em testes, substituído por uma função que registra/executa o job localmente.
_enqueue_override: Callable[[uuid.UUID, float | None], None] | None = None


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(
        get_settings().redis_url, socket_connect_timeout=2, socket_timeout=10
    )


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=get_redis())


def enqueue_job(job_id: uuid.UUID, delay_seconds: float | None = None) -> None:
    if _enqueue_override is not None:
        _enqueue_override(job_id, delay_seconds)
        return
    q = get_queue()
    rq_id = f"sync-{job_id}"
    if delay_seconds:
        q.enqueue_in(
            timedelta(seconds=delay_seconds),
            "app.sync.service.run_job",
            str(job_id),
            job_id=f"{rq_id}-{int(delay_seconds)}",
            job_timeout=3600,
        )
    else:
        q.enqueue("app.sync.service.run_job", str(job_id), job_id=rq_id, job_timeout=3600)


def set_enqueue_override(fn: Callable[[uuid.UUID, float | None], None] | None) -> None:
    global _enqueue_override
    _enqueue_override = fn


class ProviderSlot:
    """Semáforo distribuído simples: limita jobs simultâneos por provedor."""

    TTL = 3600

    def __init__(self, plataforma: str) -> None:
        self.key = f"v4:sync:slots:{plataforma}"
        self.limit = get_settings().sync_max_concurrency_per_provider
        self.acquired = False

    def __enter__(self) -> bool:
        if _enqueue_override is not None:  # modo teste/síncrono
            self.acquired = True
            return True
        r = get_redis()
        n = int(r.incr(self.key))
        r.expire(self.key, self.TTL)
        if n > self.limit:
            r.decr(self.key)
            return False
        self.acquired = True
        return True

    def __exit__(self, *exc: object) -> None:
        if self.acquired and _enqueue_override is None:
            get_redis().decr(self.key)
