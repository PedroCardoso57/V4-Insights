from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.integrations.base import ExternalAccount, MetricRow, ProviderError

TOKEN_SECRETO = "EAAtokensecretometa1234567890"


class FakeProvider:
    plataforma = "meta"

    def __init__(self) -> None:
        self.contas = [
            ExternalAccount("111", "Conta Um", "BRL", "America/Sao_Paulo"),
            ExternalAccount("222", "Conta Dois", "BRL", "America/Sao_Paulo"),
        ]
        self.erros: list[ProviderError] = []
        self.chamadas = 0
        self.revogado = False
        self.on_fetch: Any = None

    def authorize_url(self, state: str, code_verifier: str) -> str:
        return f"https://provider.example/oauth?state={state}"

    def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        return {"access_token": TOKEN_SECRETO, "scopes": ["ads_read"]}

    def ensure_fresh(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        return None

    def list_accounts(self, credentials: dict[str, Any]) -> list[ExternalAccount]:
        assert credentials["access_token"] == TOKEN_SECRETO
        return self.contas

    def fetch_metrics(
        self,
        credentials: dict[str, Any],
        id_externo: str,
        nivel: str,
        inicio: date,
        fim: date,
        mapeamento: dict[str, Any],
    ) -> Iterator[MetricRow]:
        self.chamadas += 1
        if self.erros:
            raise self.erros.pop(0)
        d = inicio
        while d <= fim:
            if self.on_fetch:
                self.on_fetch()
            yield MetricRow(
                data=d,
                nivel=nivel,
                entidade_externa_id="c1",
                entidade_nome="Campanha 1",
                campanha_externa_id="c1",
                campanha_nome="Campanha 1",
                investimento=Decimal("10.00"),
                impressoes=1000,
                cliques=50,
                conversoes_detalhe={
                    "acoes": {"purchase": {"value": "2"}, "lead": {"value": "5"}},
                    "valores": {"purchase": {"value": "40"}},
                },
            )
            d += timedelta(days=1)

    def revoke(self, credentials: dict[str, Any]) -> None:
        self.revogado = True
