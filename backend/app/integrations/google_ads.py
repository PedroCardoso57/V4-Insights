"""Google Ads API (REST). Requer developer token aprovado e OAuth com escopo `adwords`.

Este OAuth é separado do login interno: usa client_id/secret próprios e solicita
`access_type=offline` para obter refresh token.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from app.config import get_settings
from app.core.oidc import pkce_challenge
from app.integrations.base import (
    ConfigProviderError,
    ExternalAccount,
    MetricRow,
    PermissionProviderError,
    http_call,
    raise_for_response,
    to_decimal,
    to_int,
)

SCOPES = ["https://www.googleapis.com/auth/adwords"]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
REVOKE_URL = "https://oauth2.googleapis.com/revoke"

_RESOURCE = {"campanha": "campaign", "conjunto": "ad_group", "anuncio": "ad_group_ad"}


def redirect_uri() -> str:
    return f"{get_settings().api_base_url.rstrip('/')}/integracoes/google_ads/callback"


class GoogleAdsProvider:
    plataforma = "google_ads"

    def __init__(self) -> None:
        s = get_settings()
        if not s.google_ads_enabled:
            raise ConfigProviderError(
                "Google Ads não configurado (GOOGLE_ADS_CLIENT_ID/SECRET/DEVELOPER_TOKEN)"
            )
        self.client_id = s.google_ads_client_id or ""
        self.client_secret = s.google_ads_client_secret or ""
        self.developer_token = s.google_ads_developer_token or ""
        self.login_customer_id = s.google_ads_login_customer_id
        self.base = f"https://googleads.googleapis.com/{s.google_ads_api_version}"

    # --- OAuth -------------------------------------------------------------

    def authorize_url(self, state: str, code_verifier: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri(),
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "false",
            "state": state,
            "code_challenge": pkce_challenge(code_verifier),
            "code_challenge_method": "S256",
        }
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        resp = http_call(
            "POST",
            TOKEN_URL,
            data={
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
        raise_for_response(resp, permission_codes={400})
        data = resp.json()
        scopes = (data.get("scope") or "").split()
        if SCOPES[0] not in scopes:
            raise PermissionProviderError("escopo adwords não concedido")
        if not data.get("refresh_token"):
            raise PermissionProviderError("refresh token não retornado; refaça o consentimento")
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": time.time() + int(data.get("expires_in", 3600)),
            "scopes": scopes,
        }

    def ensure_fresh(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        if credentials.get("expires_at", 0) - 120 > time.time():
            return None
        resp = http_call(
            "POST",
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": credentials["refresh_token"],
                "grant_type": "refresh_token",
            },
        )
        # invalid_grant (400) = refresh token revogado/expirado → reconexão necessária.
        raise_for_response(resp, permission_codes={400})
        data = resp.json()
        new = dict(credentials)
        new["access_token"] = data["access_token"]
        new["expires_at"] = time.time() + int(data.get("expires_in", 3600))
        return new

    def revoke(self, credentials: dict[str, Any]) -> None:
        token = credentials.get("refresh_token") or credentials.get("access_token")
        resp = http_call("POST", REVOKE_URL, data={"token": token})
        raise_for_response(resp)

    # --- Dados -------------------------------------------------------------

    def _headers(self, credentials: dict[str, Any]) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {credentials['access_token']}",
            "developer-token": self.developer_token,
        }
        if self.login_customer_id:
            h["login-customer-id"] = self.login_customer_id.replace("-", "")
        return h

    def list_accounts(self, credentials: dict[str, Any]) -> list[ExternalAccount]:
        resp = http_call(
            "GET",
            f"{self.base}/customers:listAccessibleCustomers",
            headers=self._headers(credentials),
        )
        raise_for_response(resp)
        out: list[ExternalAccount] = []
        for rn in resp.json().get("resourceNames", []):
            cid = rn.split("/")[-1]
            rows = list(
                self._search(
                    credentials,
                    cid,
                    "SELECT customer.id, customer.descriptive_name, customer.currency_code, "
                    "customer.time_zone, customer.manager FROM customer LIMIT 1",
                )
            )
            if not rows:
                continue
            c = rows[0].get("customer", {})
            if c.get("manager"):
                continue  # contas MCC não têm métricas próprias
            out.append(
                ExternalAccount(
                    id_externo=str(c.get("id", cid)),
                    nome=c.get("descriptiveName") or cid,
                    moeda=c.get("currencyCode"),
                    fuso=c.get("timeZone"),
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
        resource = _RESOURCE[nivel]
        select = [
            "segments.date",
            "campaign.id",
            "campaign.name",
            "metrics.cost_micros",
            "metrics.impressions",
            "metrics.clicks",
            "metrics.conversions",
            "metrics.conversions_value",
            "metrics.all_conversions",
            "metrics.all_conversions_value",
        ]
        if nivel == "conjunto":
            select += ["ad_group.id", "ad_group.name"]
        elif nivel == "anuncio":
            select += ["ad_group_ad.ad.id", "ad_group_ad.ad.name"]
        query = (
            f"SELECT {', '.join(select)} FROM {resource} "  # noqa: S608 - GAQL com valores validados
            f"WHERE segments.date BETWEEN '{inicio.isoformat()}' AND '{fim.isoformat()}'"
        )
        for row in self._search(credentials, id_externo, query):
            m = row.get("metrics", {})
            camp = row.get("campaign", {})
            if nivel == "campanha":
                ent_id, ent_nome = camp.get("id"), camp.get("name")
            elif nivel == "conjunto":
                ent_id, ent_nome = row["adGroup"]["id"], row["adGroup"].get("name")
            else:
                ad = row["adGroupAd"]["ad"]
                ent_id, ent_nome = ad["id"], ad.get("name")
            yield MetricRow(
                data=date.fromisoformat(row["segments"]["date"]),
                nivel=nivel,
                entidade_externa_id=str(ent_id),
                entidade_nome=ent_nome,
                campanha_externa_id=str(camp.get("id")) if camp.get("id") else None,
                campanha_nome=camp.get("name"),
                investimento=(to_decimal(m.get("costMicros")) / Decimal(1_000_000)),
                impressoes=to_int(m.get("impressions")),
                cliques=to_int(m.get("clicks")),
                conversoes_detalhe={
                    "acoes": {
                        "conversions": {"value": m.get("conversions", 0)},
                        "all_conversions": {"value": m.get("allConversions", 0)},
                    },
                    "valores": {
                        "conversions": {"value": m.get("conversionsValue", 0)},
                        "all_conversions": {"value": m.get("allConversionsValue", 0)},
                    },
                },
            )

    def _search(
        self, credentials: dict[str, Any], customer_id: str, query: str
    ) -> Iterator[dict[str, Any]]:
        cid = customer_id.replace("-", "")
        if not cid.isdigit():
            raise ValueError("customer id inválido")
        resp = http_call(
            "POST",
            f"{self.base}/customers/{cid}/googleAds:searchStream",
            headers=self._headers(credentials),
            json={"query": query},
        )
        raise_for_response(resp)
        for batch in resp.json():
            yield from batch.get("results", [])
