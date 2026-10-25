from __future__ import annotations

from decimal import Decimal

from app.services.kpis import kpis, variacao


def test_formulas_e_ausencia_em_divisao_por_zero() -> None:
    k = kpis(Decimal("150"), 15000, 300, Decimal("15"), Decimal("600"))
    assert k.ctr == Decimal("2.0000")
    assert k.cpc == Decimal("0.5000")
    assert k.cpm == Decimal("10.0000")
    assert k.cpa == Decimal("10.0000")
    assert k.roas == Decimal("4.0000")
    z = kpis(Decimal(0), 0, 0, Decimal(0), None)
    assert (z.ctr, z.cpc, z.cpm, z.cpa, z.roas) == (None, None, None, None, None)
    assert variacao(10, 0) is None and variacao(15, 10) == Decimal("50.00")
