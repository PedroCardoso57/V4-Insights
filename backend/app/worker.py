"""Processo worker: executa jobs da fila e agenda sincronizações incrementais.

Uso: python -m app.worker
"""

from __future__ import annotations

import logging
import threading
import time

import redis
from rq import Queue, SimpleWorker

from app.config import get_settings
from app.db import get_sessionmaker
from app.logging_config import configure_logging
from app.sync.queue import QUEUE_NAME, get_redis
from app.sync.service import agendar_incrementais, reenfileirar_atrasados

log = logging.getLogger("app.worker")
SCHEDULER_LOCK = "v4:sync:scheduler-lock"
TICK_SECONDS = 300


def scheduler_tick() -> None:
    # Apenas uma réplica agenda por vez.
    r = get_redis()
    if not r.set(SCHEDULER_LOCK, "1", nx=True, ex=TICK_SECONDS - 10):
        return
    db = get_sessionmaker()()
    try:
        criados = agendar_incrementais(db)
        recuperados = reenfileirar_atrasados(db)
        if criados or recuperados:
            log.info("agendador: %s incrementais, %s reenfileirados", criados, recuperados)
    finally:
        db.close()


def _scheduler_loop(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            scheduler_tick()
        except Exception:
            log.exception("falha no agendador")
        stop.wait(TICK_SECONDS)


def main() -> None:
    settings = get_settings()  # valida configuração na inicialização
    configure_logging(settings.log_level)
    stop = threading.Event()
    t = threading.Thread(target=_scheduler_loop, args=(stop,), daemon=True)
    t.start()
    # Conexão própria, sem socket_timeout: o worker usa BLPOP de longa duração.
    conn = redis.Redis.from_url(settings.redis_url)
    # SimpleWorker (sem fork) mantém o pool de conexões do SQLAlchemy válido.
    worker = SimpleWorker([Queue(QUEUE_NAME, connection=conn)], connection=conn)
    try:
        worker.work(with_scheduler=True)
    finally:
        stop.set()
        time.sleep(0.1)


if __name__ == "__main__":
    main()
