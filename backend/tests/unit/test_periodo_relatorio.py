from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import PeriodoRelatorio
from app.services.pdf import fmt_kpi
from app.services.relatorios import resolver_periodo

HOJE = date(2026, 3, 15)


@pytest.mark.parametrize(
    ("tipo", "esperado"),
    [
        ("ultimos_7_dias", (date(2026, 3, 9), HOJE)),
        ("ultimos_30_dias", (date(2026, 2, 14), HOJE)),
        ("mes_atual", (date(2026, 3, 1), HOJE)),
        ("mes_anterior", (date(2026, 2, 1), date(2026, 2, 28))),
    ],
)
def test_periodos_relativos(tipo: str, esperado: tuple[date, date]) -> None:
    assert resolver_periodo(PeriodoRelatorio(tipo=tipo), HOJE) == esperado  # type: ignore[arg-type]


def test_periodo_personalizado_validado() -> None:
    p = PeriodoRelatorio(tipo="personalizado", inicio=date(2026, 1, 1), fim=date(2026, 1, 31))
    assert resolver_periodo(p, HOJE) == (date(2026, 1, 1), date(2026, 1, 31))
    with pytest.raises(ValidationError):
        PeriodoRelatorio(tipo="personalizado", inicio=date(2026, 2, 1), fim=date(2026, 1, 1))
    with pytest.raises(ValidationError):
        PeriodoRelatorio(tipo="personalizado")


def test_formatacao_pdf() -> None:
    assert fmt_kpi("investimento", "1234.5") == "R$ 1.234,50"
    assert fmt_kpi("ctr", "2.5") == "2,50%"
    assert fmt_kpi("roas", None) == "—"
    assert fmt_kpi("impressoes", 15000) == "15.000"
