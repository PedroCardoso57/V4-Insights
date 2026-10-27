"""LinkedIn Marketing API (REST versionada). Requer app com o produto Advertising API
aprovado e os escopos `r_ads` (contas) e `r_ads_reporting` (métricas).

Hierarquia do LinkedIn mapeada para os níveis do V4 Insights:
grupo de campanhas → campanha, campanha → conjunto, criativo → anúncio.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import date
from typing import Any
from urllib.parse import quote, urlencode

from app.core.config import get_settings
from app.integrations.base import (
    ConfigProviderError,
    ExternalAccount,
    MetricRow,
    PermissionProviderError,
    http_call,
    janelas,
    raise_for_response,
    to_decimal,
    to_int,
)

SCOPES = ["r_ads", "r_ads_reporting"]
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"  # noqa: S105
REVOKE_URL = "https://www.linkedin.com/oauth/v2/revoke"
API_URL = "https://api.linkedin.com/rest"

# Pivôs do adAnalytics por nível (o último é a entidade da linha).
_PIVOTS = {
    "campanha": ["CAMPAIGN_GROUP"],
    "conjunto": ["CAMPAIGN_GROUP", "CAMPAIGN"],
    "anuncio": ["CAMPAIGN_GROUP", "CAMPAIGN", "CREATIVE"],
}
_FIELDS = [
    "dateRange",
    "pivotValues",
    "costInLocalCurrency",
    "impressions",
    "clicks",
    "externalWebsiteConversions",
    "conversionValueInLocalCurrency",
    "oneClickLeads",
]
# A API responde no máximo 15 mil linhas por chamada, sem paginação: janelas curtas.
_JANELA_DIAS = 30


def redirect_uri() -> str:
    return f"{get_settings().api_v1_url}/integracoes/linkedin_ads/callback"


def _id_da_urn(urn: str) -> str:
    return urn.rsplit(":", 1)[-1]


def _data_restli(d: date) -> str:
    return f"(year:{d.year},month:{d.month},day:{d.day})"


class LinkedInProvider:
    plataforma = "linkedin_ads"

    def __init__(self) -> None:
        s = get_settings()
        if not s.linkedin_enabled:
            raise ConfigProviderError(
                "LinkedIn não configurado (LINKEDIN_CLIENT_ID/LINKEDIN_CLIENT_SECRET)"
            )
        self.client_id = s.linkedin_client_id or ""
        self.client_secret = s.linkedin_client_secret or ""
        self.version = s.linkedin_api_version

    # --- OAuth -------------------------------------------------------------

    def authorize_url(self, state: str, code_verifier: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri(),
            "state": state,
            "scope": " ".join(SCOPES),
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        resp = http_call(
            "POST",
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri(),
            },
        )
        raise_for_response(resp, permission_codes={400})
        data = resp.json()
        scopes = [s for s in (data.get("scope") or "").replace(" ", ",").split(",") if s]
        if faltando := [s for s in SCOPES if s not in scopes]:
            raise PermissionProviderError(f"escopos não concedidos: {', '.join(faltando)}")
        return self._credenciais(data, scopes)

    def ensure_fresh(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        if credentials.get("expires_at", 0) - 120 > time.time():
            return None
        if not credentials.get("refresh_token"):
            # Apps sem refresh programático recebem só o access token (~60 dias).
            raise PermissionProviderError("token do LinkedIn expirado; reconecte a integração")
        resp = http_call(
            "POST",
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": credentials["refresh_token"],
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        raise_for_response(resp, permission_codes={400})
        return self._credenciais(resp.json(), list(credentials.get("scopes") or []), credentials)

    def revoke(self, credentials: dict[str, Any]) -> None:
        resp = http_call(
            "POST",
            REVOKE_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "token": credentials["access_token"],
            },
        )
        raise_for_response(resp)

    @staticmethod
    def _credenciais(
        data: dict[str, Any], scopes: list[str], anteriores: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        creds = dict(anteriores or {})
        creds["access_token"] = data["access_token"]
        creds["expires_at"] = time.time() + int(data.get("expires_in", 5_184_000))
        creds["scopes"] = scopes
        if data.get("refresh_token"):
            creds["refresh_token"] = data["refresh_token"]
        return creds

    # --- Dados -------------------------------------------------------------

    def list_accounts(self, credentials: dict[str, Any]) -> list[ExternalAccount]:
        out: list[ExternalAccount] = []
        for item in self._paginate(credentials, "/adAccounts", "q=search"):
            if item.get("test"):
                continue
            out.append(
                ExternalAccount(
                    id_externo=str(item["id"]),
                    nome=item.get("name") or str(item["id"]),
                    moeda=item.get("currency"),
                    fuso="UTC",  # o adAnalytics agrega os dias em UTC
                )
            )
        return out

    def fetch_metrics(
        self,
        credentials: dict[str, Any],
        id_externo: str,
        nivel: str,
        inicio: date,
        fim: date,
        mapeamento: dict[str, Any],
    ) -> Iterator[MetricRow]:
        if not id_externo.isdigit():
            raise ValueError("id de conta LinkedIn inválido")
        pivots = _PIVOTS[nivel]
        nomes_grupos = self._nomes(credentials, f"/adAccounts/{id_externo}/adCampaignGroups")
        nomes_camp = (
            self._nomes(credentials, f"/adAccounts/{id_externo}/adCampaigns")
            if nivel != "campanha"
            else {}
        )
        conta = quote(f"urn:li:sponsoredAccount:{id_externo}", safe="")
        for ini, fi in janelas(inicio, fim, _JANELA_DIAS):
            query = (
                "q=statistics"
                f"&pivots=List({','.join(pivots)})"
                "&timeGranularity=DAILY"
                f"&dateRange=(start:{_data_restli(ini)},end:{_data_restli(fi)})"
                f"&accounts=List({conta})"
                f"&fields={','.join(_FIELDS)}"
            )
            data = self._get(credentials, "/adAnalytics", query)
            for el in data.get("elements", []):
                ids = [_id_da_urn(v) for v in el.get("pivotValues") or []]
                if len(ids) != len(pivots):
                    continue
                st = (el.get("dateRange") or {}).get("start") or {}
                grupo_id = ids[0]
                camp_id = ids[1] if len(ids) > 1 else None
                ent_id = ids[-1]
                if nivel == "campanha":
                    ent_nome = nomes_grupos.get(ent_id)
                elif nivel == "conjunto":
                    ent_nome = nomes_camp.get(ent_id)
                else:
                    ent_nome = None  # criativos não têm nome próprio na API
                yield MetricRow(
                    data=date(int(st["year"]), int(st["month"]), int(st["day"])),
                    nivel=nivel,
                    entidade_externa_id=ent_id,
                    entidade_nome=ent_nome,
                    campanha_externa_id=grupo_id,
                    campanha_nome=nomes_grupos.get(grupo_id),
                    conjunto_externo_id=camp_id,
                    conjunto_nome=nomes_camp.get(camp_id) if camp_id else None,
                    investimento=to_decimal(el.get("costInLocalCurrency")),
                    impressoes=to_int(el.get("impressions")),
                    cliques=to_int(el.get("clicks")),
                    conversoes_detalhe={
                        "acoes": {
                            "external_website_conversions": {
                                "value": el.get("externalWebsiteConversions") or 0
                            },
                            "one_click_leads": {"value": el.get("oneClickLeads") or 0},
                        },
                        "valores": {
                            "external_website_conversions": {
                                "value": el.get("conversionValueInLocalCurrency") or 0
                            },
                        },
                    },
                )

    def _nomes(self, credentials: dict[str, Any], path: str) -> dict[str, str]:
        return {
            str(i["id"]): i.get("name") or str(i["id"])
            for i in self._paginate(credentials, path, "q=search")
        }

    # --- HTTP --------------------------------------------------------------

    def _headers(self, credentials: dict[str, Any]) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credentials['access_token']}",
            "LinkedIn-Version": self.version,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _paginate(
        self, credentials: dict[str, Any], path: str, query: str
    ) -> Iterator[dict[str, Any]]:
        token: str | None = None
        while True:
            q = f"{query}&pageSize=100"
            if token:
                q += f"&pageToken={quote(token, safe='')}"
            data = self._get(credentials, path, q)
            yield from data.get("elements", [])
            token = (data.get("metadata") or {}).get("nextPageToken")
            if not token:
                return

    def _get(self, credentials: dict[str, Any], path: str, query: str) -> dict[str, Any]:
        # Rest.li 2.0 exige parênteses e vírgulas literais: a query já vem codificada.
        resp = http_call("GET", f"{API_URL}{path}?{query}", headers=self._headers(credentials))
        raise_for_response(resp)
        result: dict[str, Any] = resp.json()
        return result
