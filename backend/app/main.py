from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_config import configure_logging
from app.routers import (
    auditoria,
    auth,
    clientes,
    dashboards,
    health,
    integracoes,
    metricas,
    usuarios,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    settings = get_settings()  # falha cedo se a configuração for inválida
    configure_logging(settings.log_level)
    app = FastAPI(
        title="V4 Insights API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
    for r in (health, auth, usuarios, clientes, integracoes, metricas, dashboards, auditoria):
        app.include_router(r.router)
    return app


app = create_app()
