from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import errors, health
from app.api.errors import ERROR_RESPONSES
from app.api.v1.routes import (
    auditoria,
    auth,
    clientes,
    dashboards,
    integracoes,
    metricas,
    relatorios,
    usuarios,
)
from app.core.config import get_settings
from app.core.logging import configure_logging

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()  # falha cedo se a configuração for inválida
    configure_logging(settings.log_level)
    app = FastAPI(
        title="V4 Insights API",
        version="0.2.0",
        description="API interna da V4 Bounnacorso. Erros seguem o envelope "
        '`{"error": {"code", "message", "request_id"}}`.',
        docs_url="/docs" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID", "Idempotency-Key"],
        expose_headers=["X-Request-ID"],
    )
    errors.install(app)
    app.include_router(health.router)  # /health/live e /health/ready (fora do versionamento)
    v1 = APIRouter(prefix=API_PREFIX, responses=ERROR_RESPONSES)
    for r in (auth, usuarios, clientes, integracoes, metricas, dashboards, relatorios, auditoria):
        v1.include_router(r.router)
    app.include_router(v1)
    return app


app = create_app()
