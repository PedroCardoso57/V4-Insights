from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.session import get_engine
from app.workers.queue import get_redis

router = APIRouter(prefix="/health", tags=["health"])
log = logging.getLogger(__name__)


@router.get("/live")
def live() -> dict[str, str]:
    """Processo de pé; não consulta dependências."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    """Prontidão: banco e Redis são críticos (Redis sustenta a fila de sincronização)."""
    checks: dict[str, str] = {}
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        log.warning("readiness: banco indisponível: %s", exc.__class__.__name__)
        checks["database"] = "indisponivel"
    try:
        get_redis().ping()
        checks["redis"] = "ok"
    except Exception as exc:
        log.warning("readiness: redis indisponível: %s", exc.__class__.__name__)
        checks["redis"] = "indisponivel"
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if ok else "indisponivel", "checks": checks}, status_code=200 if ok else 503
    )
