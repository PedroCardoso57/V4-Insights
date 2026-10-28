"""Contrato comum dos provedores de anúncios e normalização de métricas."""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Protocol

import httpx

from app.core.sanitize import sanitize


class ProviderError(Exception):
    """Erro de provedor. `retryable` indica se é seguro repetir automaticamente."""

    retryable = False

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(sanitize(message))
        self.retry_after = retry_after


class RetryableProviderError(ProviderError):
    """429, 5xx e falhas de rede: retry exponencial controlado."""

    retryable = True


class PermissionProviderError(ProviderError):
    """Token revogado, escopo insuficiente, conta sem acesso: nunca repetir sozinho."""


DICA_CONFIGURACAO = "cadastre as chaves em Configurações > Chaves das plataformas (ou no .env)"


class ConfigProviderError(ProviderError):
    """Provedor não configurado neste ambiente."""


@dataclass
class ExternalAccount:
    id_externo: str
    nome: str
    moeda: str | None = None
    fuso: str | None = None


@dataclass
class MetricRow:
    data: date
    nivel: str
    entidade_externa_id: str
    entidade_nome: str | None
    campanha_externa_id: str | None
    campanha_nome: str | None
    investimento: Decimal
    impressoes: int
    cliques: int
    conjunto_externo_id: str | None = None
    conjunto_nome: str | None = None
    # {"acoes": {tipo: {janela: n}}, "valores": {tipo: {janela: n}}}
    conversoes_detalhe: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)


class AdsProvider(Protocol):
    plataforma: str

    def authorize_url(self, state: str, code_verifier: str) -> str: ...

    def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]: ...

    def ensure_fresh(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        """Devolve credenciais renovadas (para regravar) ou None se inalteradas."""
        ...

    def list_accounts(self, credentials: dict[str, Any]) -> list[ExternalAccount]: ...

    def fetch_metrics(
        self,
        credentials: dict[str, Any],
        id_externo: str,
        nivel: str,
        inicio: date,
        fim: date,
        mapeamento: dict[str, Any],
    ) -> Iterator[MetricRow]: ...

    def revoke(self, credentials: dict[str, Any]) -> None: ...


def raise_for_response(resp: httpx.Response, permission_codes: set[int] | None = None) -> None:
    """Classifica respostas HTTP de provedores em erros retryable ou definitivos."""
    if resp.is_success:
        return
    code = resp.status_code
    detail = resp.text[:500]
    retry_after: float | None = None
    if ra := resp.headers.get("retry-after"):
        try:
            retry_after = float(ra)
        except ValueError:
            retry_after = None
    if code == 429 or code >= 500:
        raise RetryableProviderError(f"HTTP {code}: {detail}", retry_after=retry_after)
    if code in (401, 403) or (permission_codes and code in permission_codes):
        raise PermissionProviderError(f"HTTP {code}: {detail}")
    raise ProviderError(f"HTTP {code}: {detail}")


def http_call(method: str, url: str, **kw: Any) -> httpx.Response:
    try:
        return httpx.request(method, url, timeout=kw.pop("timeout", 60), **kw)
    except httpx.TimeoutException as exc:
        raise RetryableProviderError("timeout ao chamar provedor") from exc
    except httpx.TransportError as exc:
        raise RetryableProviderError(f"falha de rede: {exc.__class__.__name__}") from exc


def backoff_seconds(tentativa: int, base: float = 30.0, cap: float = 3600.0) -> float:
    """Backoff exponencial com jitter: 30s, 60s, 120s... até 1h."""
    delay: float = min(cap, base * (2 ** max(0, tentativa - 1)))
    return delay * (0.8 + random.random() * 0.4)  # noqa: S311 - jitter, não criptográfico


def janelas(inicio: date, fim: date, dias: int) -> Iterator[tuple[date, date]]:
    """Divide [inicio, fim] em janelas de até `dias` dias (limites de período dos provedores)."""
    atual = inicio
    while atual <= fim:
        ate = min(fim, atual + timedelta(days=dias - 1))
        yield atual, ate
        atual = ate + timedelta(days=1)


def to_decimal(v: Any) -> Decimal:
    if v is None or v == "":
        return Decimal(0)
    return Decimal(str(v))


def to_int(v: Any) -> int:
    if v is None or v == "":
        return 0
    return int(Decimal(str(v)))


def aplicar_mapeamento(
    detalhe: dict[str, Any], mapeamento: dict[str, Any]
) -> tuple[Decimal | None, Decimal | None]:
    """Calcula (conversoes, valor_conversoes) a partir do mapeamento explícito.

    Sem `action_types` no mapeamento, ambos ficam ausentes (None): conversões de
    plataformas diferentes não são equiparadas implicitamente.
    """
    tipos = mapeamento.get("action_types") or []
    if not tipos:
        return None, None
    janela = mapeamento.get("janela") or "value"
    acoes = detalhe.get("acoes") or {}
    valores = detalhe.get("valores") or {}
    total = Decimal(0)
    total_valor = Decimal(0)
    tem_valor = False
    for t in tipos:
        total += to_decimal((acoes.get(t) or {}).get(janela))
        v = (valores.get(t) or {}).get(janela)
        if v is not None:
            tem_valor = True
            total_valor += to_decimal(v)
    return total, (total_valor if tem_valor else None)
