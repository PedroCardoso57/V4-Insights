"""Cálculo de KPIs (SPEC-04). Divisão por zero resulta em valor ausente (None)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.schemas import Kpis

Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")


def _div(a: Decimal | int | None, b: Decimal | int | None, mult: int = 1) -> Decimal | None:
    if a is None or b is None:
        return None
    b = Decimal(b)
    if b == 0:
        return None
    return (Decimal(a) * mult / b).quantize(Q4, rounding=ROUND_HALF_UP)


def kpis(
    investimento: Decimal | None,
    impressoes: int | None,
    cliques: int | None,
    conversoes: Decimal | None,
    valor_conversoes: Decimal | None,
) -> Kpis:
    inv = (
        Decimal(investimento).quantize(Q2, rounding=ROUND_HALF_UP)
        if investimento is not None
        else None
    )
    return Kpis(
        investimento=inv,
        impressoes=int(impressoes) if impressoes is not None else None,
        cliques=int(cliques) if cliques is not None else None,
        conversoes=Decimal(conversoes).quantize(Q2) if conversoes is not None else None,
        valor_conversoes=Decimal(valor_conversoes).quantize(Q2)
        if valor_conversoes is not None
        else None,
        ctr=_div(cliques, impressoes, 100),
        cpc=_div(investimento, cliques),
        cpm=_div(investimento, impressoes, 1000),
        cpa=_div(investimento, conversoes),
        # ROAS só quando existe valor de conversões confiável (mapeado).
        roas=_div(valor_conversoes, investimento) if valor_conversoes is not None else None,
    )


def kpis_from_row(row: Any) -> Kpis:
    return kpis(row.investimento, row.impressoes, row.cliques, row.conversoes, row.valor_conversoes)


def variacao(atual: Decimal | int | None, anterior: Decimal | int | None) -> Decimal | None:
    """Variação percentual; ausente quando o período anterior é zero ou inexistente."""
    if atual is None or anterior is None:
        return None
    anterior = Decimal(anterior)
    if anterior == 0:
        return None
    return ((Decimal(atual) - anterior) * 100 / anterior).quantize(Q2, rounding=ROUND_HALF_UP)


def variacoes(atual: Kpis, anterior: Kpis | None) -> dict[str, Decimal | None]:
    campos = list(Kpis.model_fields)
    if anterior is None:
        return dict.fromkeys(campos)
    return {c: variacao(getattr(atual, c), getattr(anterior, c)) for c in campos}
