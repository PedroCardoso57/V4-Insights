"""Métricas operacionais (SPEC-07) no formato Prometheus.

`GET /metrics` é servido só na rede interna: o proxy não encaminha esse caminho.
Métricas de jobs são calculadas do banco no momento da coleta, então refletem também o que
o worker (outro processo) executou.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector
from sqlalchemy import func, select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REGISTRY = CollectorRegistry()
HTTP_REQ = Counter(
    "v4_http_requests_total", "Requisições HTTP", ["method", "route", "status"], registry=REGISTRY
)
HTTP_LAT = Histogram(
    "v4_http_request_duration_seconds",
    "Latência HTTP",
    ["method", "route"],
    registry=REGISTRY,
    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        inicio = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            rota = request.scope.get("route")
            # Template da rota (ex.: /api/v1/clientes/{cliente_id}) evita cardinalidade alta.
            nome = getattr(rota, "path", "nao_roteado")
            HTTP_REQ.labels(request.method, nome, str(status)).inc()
            HTTP_LAT.labels(request.method, nome).observe(time.perf_counter() - inicio)


class ColetorNegocio(Collector):
    def collect(self) -> Iterator[GaugeMetricFamily]:
        from app.db.session import get_sessionmaker
        from app.models import ContaAnuncio, Integracao, RelatorioExecucao, SyncJob

        db = get_sessionmaker()()
        try:
            desde = datetime.now(UTC) - timedelta(hours=24)
            jobs = GaugeMetricFamily(
                "v4_sync_jobs_24h", "Jobs de sincronização (24h) por status", labels=["status"]
            )
            for st, n in db.execute(
                select(SyncJob.status, func.count())
                .where(SyncJob.criado_em >= desde)
                .group_by(SyncJob.status)
            ):
                jobs.add_metric([st], n)
            yield jobs
            integ = GaugeMetricFamily(
                "v4_integracoes",
                "Integrações por plataforma e status",
                labels=["plataforma", "status"],
            )
            for pl, st, n in db.execute(
                select(Integracao.plataforma, Integracao.status, func.count()).group_by(
                    Integracao.plataforma, Integracao.status
                )
            ):
                integ.add_metric([pl, st], n)
            yield integ
            pend = db.scalar(
                select(func.min(SyncJob.criado_em)).where(SyncJob.status == "pendente")
            )
            idade = GaugeMetricFamily(
                "v4_sync_job_pendente_mais_antigo_segundos", "Idade do job pendente mais antigo"
            )
            idade.add_metric([], (datetime.now(UTC) - pend).total_seconds() if pend else 0)
            yield idade
            atrasadas = db.scalar(
                select(func.count())
                .select_from(ContaAnuncio)
                .join(Integracao)
                .where(
                    Integracao.status == "conectada",
                    ContaAnuncio.ativa.is_(True),
                    (ContaAnuncio.ultima_sincronizacao_em.is_(None))
                    | (
                        ContaAnuncio.ultima_sincronizacao_em
                        < datetime.now(UTC) - timedelta(hours=24)
                    ),
                )
            )
            g = GaugeMetricFamily("v4_contas_desatualizadas", "Contas ativas sem sync há 24h")
            g.add_metric([], atrasadas or 0)
            yield g
            rel = GaugeMetricFamily(
                "v4_relatorio_execucoes_24h", "Execuções de PDF (24h)", labels=["status"]
            )
            for st, n in db.execute(
                select(RelatorioExecucao.status, func.count())
                .where(RelatorioExecucao.iniciado_em >= desde)
                .group_by(RelatorioExecucao.status)
            ):
                rel.add_metric([st], n)
            yield rel
        except Exception:  # banco fora: métricas HTTP continuam disponíveis
            return
        finally:
            db.close()


REGISTRY.register(ColetorNegocio())


def resposta_metricas() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
