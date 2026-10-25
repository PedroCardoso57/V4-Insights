from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.integrations.base import AdsProvider
from app.models import Plataforma

_factories: dict[str, Callable[[], AdsProvider]] = {}


def _defaults() -> dict[str, Callable[[], Any]]:
    from app.integrations.google_ads import GoogleAdsProvider
    from app.integrations.meta import MetaProvider

    return {Plataforma.meta_ads.value: MetaProvider, Plataforma.google_ads.value: GoogleAdsProvider}


def get_provider(plataforma: str) -> AdsProvider:
    factory = _factories.get(plataforma) or _defaults().get(plataforma)
    if factory is None:
        raise KeyError(plataforma)
    return factory()


def override_provider(plataforma: str, factory: Callable[[], AdsProvider] | None) -> None:
    """Usado em testes para injetar provedores falsos."""
    if factory is None:
        _factories.pop(plataforma, None)
    else:
        _factories[plataforma] = factory


def mapeamento_padrao(plataforma: str) -> dict[str, Any]:
    # Google Ads: conversões primárias configuradas na própria conta são o mapeamento
    # explícito inicial. Meta: nenhum até que o analista escolha os action_types.
    if plataforma == Plataforma.google_ads.value:
        return {"action_types": ["conversions"]}
    return {}
