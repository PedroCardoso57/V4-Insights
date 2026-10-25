"""Meta Marketing API (Graph API). Requer app aprovado com permissão `ads_read`."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from typing import Any
from urllib.parse import urlencode

from app.config import get_settings
from app.integrations.base import (
    ConfigProviderError,
    ExternalAccount,
    MetricRow,
    PermissionProviderError,
    ProviderError,
    RetryableProviderError,
    http_call,
    raise_for_response,
    to_decimal,
    to_int,
)

SCOPES = ["ads_read"]
# Códigos de erro Graph: 4/17/32/613/80000-80014 = rate limit; 190 = token inválido;
# 10/200-299 = permissão.
_RATE_LIMIT_CODES = {4, 17, 32, 613} | set(range(80000, 80015))
_LEVEL = {"campanha": "campaign", "conjunto": "adset", "anuncio": "ad"}
_ID_FIELD = {"campanha": "campaign", "conjunto": "adset", "anuncio": "ad"}


def redirect_uri() -> str:
    return f"{get_settings().api_base_url.rstrip('/')}/integracoes/meta/callback"


class MetaProvider:
    plataforma = "meta"

    def __init__(self) -> None:
        s = get_settings()
        if not s.meta_enabled:
            raise ConfigProviderError("Meta não configurado (META_APP_ID/META_APP_SECRET)")
        self.app_id = s.meta_app_id or ""
        self.app_secret = s.meta_app_secret or ""
        self.base = f"https://graph.facebook.com/{s.meta_graph_version}"
        self.dialog = f"https://www.facebook.com/{s.meta_graph_version}/dialog/oauth"

    # --- OAuth -------------------------------------------------------------

    def authorize_url(self, state: str, code_verifier: str) -> str:
        params = {
            "client_id": self.app_id,
            "redirect_uri": redirect_uri(),
            "state": state,
            "scope": ",".join(SCOPES),
            "response_type": "code",
        }
        return f"{self.dialog}?{urlencode(params)}"

    def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        short = self._get(
            "/oauth/access_token",
            {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri": redirect_uri(),
                "code": code,
            },
            auth=False,
        )
        # Troca por token de longa duração (~60 dias).
        long = self._get(
            "/oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": short["access_token"],
            },
            auth=False,
        )
        perms = self._get("/me/permissions", {}, token=long["access_token"])
        granted = [p["permission"] for p in perms.get("data", []) if p.get("status") == "granted"]
        if "ads_read" not in granted:
            raise PermissionProviderError("permissão ads_read não concedida")
        return {
            "access_token": long["access_token"],
            "expires_in": long.get("expires_in"),
            "scopes": granted,
        }

    def ensure_fresh(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        return None  # tokens de longa duração; ao expirar, a integração pede reconexão

    def revoke(self, credentials: dict[str, Any]) -> None:
        resp = http_call(
            "DELETE",
            f"{self.base}/me/permissions",
            params={"access_token": credentials["access_token"]},
        )
        self._check(resp)

    # --- Dados -------------------------------------------------------------

    def list_accounts(self, credentials: dict[str, Any]) -> list[ExternalAccount]:
        out: list[ExternalAccount] = []
        for item in self._paginate(
            "/me/adaccounts",
            {
                "fields": "account_id,name,currency,timezone_name,account_status",
                "limit": 200,
            },
            credentials["access_token"],
        ):
            out.append(
                ExternalAccount(
                    id_externo=str(item["account_id"]),
                    nome=item.get("name") or str(item["account_id"]),
                    moeda=item.get("currency"),
                    fuso=item.get("timezone_name"),
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
        level = _LEVEL[nivel]
        idf = _ID_FIELD[nivel]
        fields = [
            "campaign_id",
            "campaign_name",
            "spend",
            "impressions",
            "clicks",
            "actions",
            "action_values",
            "date_start",
            "account_currency",
        ]
        if idf != "campaign":
            fields += [f"{idf}_id", f"{idf}_name"]
        params: dict[str, Any] = {
            "level": level,
            "time_increment": 1,
            "time_range": json.dumps({"since": inicio.isoformat(), "until": fim.isoformat()}),
            "fields": ",".join(fields),
            "limit": 500,
        }
        # Janela explícita (ex.: "7d_click") no mapeamento; sem ela, padrão da conta.
        if janela := mapeamento.get("janela"):
            params["action_attribution_windows"] = json.dumps([janela])
        for item in self._paginate(
            f"/act_{id_externo}/insights", params, credentials["access_token"]
        ):
            yield MetricRow(
                data=date.fromisoformat(item["date_start"]),
                nivel=nivel,
                entidade_externa_id=str(item[f"{idf}_id"]),
                entidade_nome=item.get(f"{idf}_name"),
                campanha_externa_id=item.get("campaign_id"),
                campanha_nome=item.get("campaign_name"),
                investimento=to_decimal(item.get("spend")),
                impressoes=to_int(item.get("impressions")),
                cliques=to_int(item.get("clicks")),
                conversoes_detalhe={
                    "acoes": _actions(item.get("actions")),
                    "valores": _actions(item.get("action_values")),
                },
            )

    # --- HTTP --------------------------------------------------------------

    def _paginate(self, path: str, params: dict[str, Any], token: str) -> Iterator[dict[str, Any]]:
        data = self._get(path, params, token=token)
        while True:
            yield from data.get("data", [])
            nxt = (data.get("paging") or {}).get("next")
            if not nxt:
                return
            resp = http_call("GET", nxt)  # URL já contém o token
            self._check(resp)
            data = resp.json()

    def _get(
        self, path: str, params: dict[str, Any], *, token: str | None = None, auth: bool = True
    ) -> dict[str, Any]:
        p = dict(params)
        if auth:
            p["access_token"] = token
        resp = http_call("GET", f"{self.base}{path}", params=p)
        self._check(resp)
        result: dict[str, Any] = resp.json()
        return result

    @staticmethod
    def _check(resp: Any) -> None:
        if resp.is_success:
            return
        try:
            err = resp.json().get("error", {})
        except ValueError:
            err = {}
        code = err.get("code")
        msg = f"Meta {resp.status_code} code={code}: {err.get('message', '')[:300]}"
        if code in _RATE_LIMIT_CODES:
            raise RetryableProviderError(msg)
        if code == 190 or code == 10 or (isinstance(code, int) and 200 <= code < 300):
            raise PermissionProviderError(msg)
        if resp.status_code >= 500 or resp.status_code == 429 or err.get("is_transient"):
            raise RetryableProviderError(msg)
        if resp.status_code in (401, 403):
            raise PermissionProviderError(msg)
        raise_for_response(resp)
        raise ProviderError(msg)  # pragma: no cover


def _actions(items: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for a in items or []:
        tipo = a.get("action_type")
        if not tipo:
            continue
        out[tipo] = {k: v for k, v in a.items() if k != "action_type"}
    return out
