"""Versões das APIs das plataformas e quando cada uma deixa de funcionar (M01).

As plataformas desligam versões antigas: Google Ads cerca de um ano depois do lançamento,
LinkedIn no mínimo um ano depois, Meta dois anos depois da versão seguinte. Uma versão
desligada faz toda sincronização falhar, então o sistema avisa antes (`alertas.verificar`)
e mostra a situação no card Status operacional.

Fontes das datas (revisar ao trocar a versão padrão):
- Google Ads: https://developers.google.com/google-ads/api/docs/sunset-dates
- Meta: https://developers.facebook.com/docs/graph-api/changelog/versions
- LinkedIn: https://learn.microsoft.com/linkedin/marketing/versioning
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

# Versões padrão do sistema. Um valor vazio no .env, ou uma versão antiga demais, cai nelas.
META_GRAPH_VERSION_PADRAO = "v25.0"
META_GRAPH_VERSION_MINIMA = 24
GOOGLE_ADS_API_VERSION_PADRAO = "v25"
GOOGLE_ADS_API_VERSION_MINIMA = 23
LINKEDIN_API_VERSION_PADRAO = "202609"
LINKEDIN_MESES_DE_SUPORTE = 12
TIKTOK_API_VERSION_PADRAO = "v1.3"

# Datas de desligamento publicadas. Google publica só o mês; usamos o dia 1, o mais cedo.
DESLIGAMENTO: dict[tuple[str, str], date] = {
    ("google_ads", "v23"): date(2027, 2, 1),
    ("google_ads", "v24"): date(2027, 5, 1),
    ("google_ads", "v25"): date(2027, 8, 1),
    ("google_ads", "v26"): date(2027, 11, 1),
    ("meta_ads", "v25.0"): date(2028, 7, 29),
}

_AAAAMM = re.compile(r"^(\d{4})(\d{2})$")


def _mais_meses(ano: int, mes: int, meses: int) -> date:
    total = ano * 12 + (mes - 1) + meses
    return date(total // 12, total % 12 + 1, 1)


def linkedin_desligamento(versao: str) -> date | None:
    """O LinkedIn garante cada versão mensal (AAAAMM) por pelo menos 12 meses."""
    m = _AAAAMM.match(versao.strip())
    if not m:
        return None
    return _mais_meses(int(m.group(1)), int(m.group(2)), LINKEDIN_MESES_DE_SUPORTE)


def _numero(versao: str) -> int | None:
    num = versao.strip().lower().removeprefix("v").split(".")[0]
    return int(num) if num.isdigit() else None


def meta_versao_ativa(v: str | None) -> str:
    if not v or not v.strip():
        return META_GRAPH_VERSION_PADRAO
    n = _numero(v)
    if n is not None and n < META_GRAPH_VERSION_MINIMA:
        return META_GRAPH_VERSION_PADRAO
    return v.strip()


def google_ads_versao_ativa(v: str | None) -> str:
    if not v or not v.strip():
        return GOOGLE_ADS_API_VERSION_PADRAO
    n = _numero(v)
    if n is not None and n < GOOGLE_ADS_API_VERSION_MINIMA:
        return GOOGLE_ADS_API_VERSION_PADRAO
    return v.strip()


def linkedin_versao_ativa(v: str | None, hoje: date | None = None) -> str:
    if not v or not v.strip():
        return LINKEDIN_API_VERSION_PADRAO
    fim = linkedin_desligamento(v)
    if fim is not None and fim <= (hoje or date.today()):
        return LINKEDIN_API_VERSION_PADRAO
    return v.strip()


@dataclass(frozen=True)
class VersaoEmUso:
    plataforma: str
    versao: str
    desliga_em: date | None
    dias_restantes: int | None


def versoes_em_uso(hoje: date | None = None) -> list[VersaoEmUso]:
    from app.core.config import get_settings

    s = get_settings()
    hoje = hoje or date.today()
    pares = [
        ("meta_ads", s.meta_graph_version),
        ("google_ads", s.google_ads_api_version),
        ("linkedin_ads", s.linkedin_api_version),
        ("tiktok_ads", s.tiktok_api_version),
    ]
    saida: list[VersaoEmUso] = []
    for plataforma, versao in pares:
        if plataforma == "linkedin_ads":
            fim = linkedin_desligamento(versao)
        else:
            fim = DESLIGAMENTO.get((plataforma, versao))
        saida.append(
            VersaoEmUso(
                plataforma=plataforma,
                versao=versao,
                desliga_em=fim,
                dias_restantes=(fim - hoje).days if fim else None,
            )
        )
    return saida
