"""TikTok Business API (Marketing API). Requer app aprovado no TikTok for Business com
permissões de Ad Account Management e Reporting.

A API responde HTTP 200 mesmo em erro: o resultado vem em `code` (0 = sucesso).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date
from typing import Any
from urllib.parse import urlencode

from app.core.chaves import config_efetiva
from app.core.config import get_settings
from app.integrations.base import (
    DICA_CONFIGURACAO as DICA,
)
from app.integrations.base import (
    ConfigProviderError,
    ExternalAccount,
    MetricRow,
    PermissionProviderError,
    ProviderError,
    RetryableProviderError,
    http_call,
    janelas,
    raise_for_response,
    to_decimal,
    to_int,
)

AUTH_URL = "https://business-api.tiktok.com/portal/auth"
# 40100 = limite de QPS; 40001/40002 = sem permissão; 40102/40104/40105 = token inválido,
# expirado ou revogado; 5xxxx = erro interno do TikTok.
_RATE_LIMIT_CODES = {40100}
_PERMISSION_CODES = {40001, 40002, 40102, 40104, 40105, 40106}
_DATA_LEVEL = {
    "campanha": "AUCTION_CAMPAIGN",
    "conjunto": "AUCTION_ADGROUP",
    "anuncio": "AUCTION_AD",
}
_DIMENSAO = {"campanha": "campaign_id", "conjunto": "adgroup_id", "anuncio": "ad_id"}
_METRICAS = ["spend", "impressions", "clicks", "conversion", "complete_payment"]
# "total_complete_payment_rate" é, apesar do nome, o valor total das compras.
_VALOR_COMPRA = "total_complete_payment_rate"
_ATRIBUTOS = {
    "campanha": ["campaign_name"],
    "conjunto": ["campaign_id", "campaign_name", "adgroup_name"],
    "anuncio": ["campaign_id", "campaign_name", "adgroup_id", "adgroup_name", "ad_name"],
}
# Relatórios com dimensão diária aceitam no máximo 30 dias por consulta.
_JANELA_DIAS = 30


def redirect_uri() -> str:
    return f"{get_settings().api_v1_url}/integracoes/tiktok_ads/callback"


class TikTokProvider:
    plataforma = "tiktok_ads"

    def __init__(self) -> None:
        s = config_efetiva()
        if not s.tiktok_enabled:
            raise ConfigProviderError(f"TikTok Ads não configurado: {DICA}")
        self.app_id = s.tiktok_app_id or ""
        self.secret = s.tiktok_app_secret or ""
        self.base = f"https://business-api.tiktok.com/open_api/{s.tiktok_api_version}"

    # --- OAuth -------------------------------------------------------------

    def authorize_url(self, state: str, code_verifier: str) -> str:
        # Os escopos são os aprovados no app; o TikTok não aceita escopo na URL.
        params = {"app_id": self.app_id, "state": state, "redirect_uri": redirect_uri()}
        return f"{AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        data = self._call(
            "POST",
            "/oauth2/access_token/",
            json={"app_id": self.app_id, "secret": self.secret, "auth_code": code},
        )
        if not data.get("access_token"):
            raise PermissionProviderError("TikTok não retornou access token")
        return {
            "access_token": data["access_token"],
            "advertiser_ids": [str(a) for a in data.get("advertiser_ids") or []],
            "scopes": [str(s) for s in data.get("scope") or []],
        }

    def ensure_fresh(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        return None  # token de longa duração; ao ser revogado, a integração pede reconexão

    def revoke(self, credentials: dict[str, Any]) -> None:
        self._call(
            "POST",
            "/oauth2/revoke_token/",
            json={
                "app_id": self.app_id,
                "secret": self.secret,
                "access_token": credentials["access_token"],
            },
        )

    # --- Dados -------------------------------------------------------------

    def list_accounts(self, credentials: dict[str, Any]) -> list[ExternalAccount]:
        token = credentials["access_token"]
        anunciantes = self._call(
            "GET",
            "/oauth2/advertiser/get/",
            params={"app_id": self.app_id, "secret": self.secret},
            token=token,
        ).get("list", [])
        ids = [str(a["advertiser_id"]) for a in anunciantes]
        nomes = {str(a["advertiser_id"]): a.get("advertiser_name") for a in anunciantes}
        info: dict[str, dict[str, Any]] = {}
        for i in range(0, len(ids), 100):  # limite de ids por chamada
            for item in self._call(
                "GET",
                "/advertiser/info/",
                params={
                    "advertiser_ids": json.dumps(ids[i : i + 100]),
                    "fields": json.dumps(["advertiser_id", "name", "currency", "timezone"]),
                },
                token=token,
            ).get("list", []):
                info[str(item["advertiser_id"])] = item
        return [
            ExternalAccount(
                id_externo=aid,
                nome=(info.get(aid) or {}).get("name") or nomes.get(aid) or aid,
                moeda=(info.get(aid) or {}).get("currency"),
                fuso=(info.get(aid) or {}).get("timezone"),
            )
            for aid in ids
        ]

    def fetch_metrics(
        self,
        credentials: dict[str, Any],
        id_externo: str,
        nivel: str,
        inicio: date,
        fim: date,
        mapeamento: dict[str, Any],
    ) -> Iterator[MetricRow]:
        dim = _DIMENSAO[nivel]
        metricas = _METRICAS + [_VALOR_COMPRA] + _ATRIBUTOS[nivel]
        for ini, fi in janelas(inicio, fim, _JANELA_DIAS):
            page = 1
            while True:
                data = self._call(
                    "GET",
                    "/report/integrated/get/",
                    params={
                        "advertiser_id": id_externo,
                        "report_type": "BASIC",
                        "data_level": _DATA_LEVEL[nivel],
                        "dimensions": json.dumps([dim, "stat_time_day"]),
                        "metrics": json.dumps(metricas),
                        "start_date": ini.isoformat(),
                        "end_date": fi.isoformat(),
                        "page": page,
                        "page_size": 1000,
                    },
                    token=credentials["access_token"],
                )
                for item in data.get("list", []):
                    yield _linha(item, nivel, dim)
                info = data.get("page_info") or {}
                if page >= int(info.get("total_page") or 1):
                    break
                page += 1

    # --- HTTP --------------------------------------------------------------

    def _call(
        self, method: str, path: str, *, token: str | None = None, **kw: Any
    ) -> dict[str, Any]:
        headers = {"Access-Token": token} if token else {}
        resp = http_call(method, f"{self.base}{path}", headers=headers, **kw)
        raise_for_response(resp)
        body = resp.json()
        code = body.get("code")
        if code == 0:
            result: dict[str, Any] = body.get("data") or {}
            return result
        msg = f"TikTok code={code}: {str(body.get('message', ''))[:300]}"
        if code in _RATE_LIMIT_CODES or (isinstance(code, int) and code >= 50000):
            raise RetryableProviderError(msg)
        if code in _PERMISSION_CODES:
            raise PermissionProviderError(msg)
        raise ProviderError(msg)


def _linha(item: dict[str, Any], nivel: str, dim: str) -> MetricRow:
    d = item.get("dimensions") or {}
    m = item.get("metrics") or {}
    ent_id = str(d[dim])
    camp_id = ent_id if nivel == "campanha" else m.get("campaign_id")
    if nivel == "conjunto":
        grupo_id: str | None = ent_id
    else:
        grupo_id = m.get("adgroup_id")
    nome = {"campanha": "campaign_name", "conjunto": "adgroup_name", "anuncio": "ad_name"}[nivel]
    return MetricRow(
        data=date.fromisoformat(str(d["stat_time_day"])[:10]),
        nivel=nivel,
        entidade_externa_id=ent_id,
        entidade_nome=m.get(nome),
        campanha_externa_id=str(camp_id) if camp_id else None,
        campanha_nome=m.get("campaign_name"),
        conjunto_externo_id=str(grupo_id) if grupo_id else None,
        conjunto_nome=m.get("adgroup_name"),
        investimento=to_decimal(m.get("spend")),
        impressoes=to_int(m.get("impressions")),
        cliques=to_int(m.get("clicks")),
        conversoes_detalhe={
            "acoes": {
                "conversion": {"value": m.get("conversion") or 0},
                "complete_payment": {"value": m.get("complete_payment") or 0},
            },
            "valores": {"complete_payment": {"value": m.get(_VALOR_COMPRA) or 0}},
        },
    )
