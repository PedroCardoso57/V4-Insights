"""Provedores LinkedIn Ads e TikTok Ads contra respostas simuladas das APIs."""

from __future__ import annotations

import json
from datetime import date
from urllib.parse import parse_qs, unquote, urlsplit

import httpx
import pytest
import respx

from app.integrations.base import (
    PermissionProviderError,
    RetryableProviderError,
    aplicar_mapeamento,
    janelas,
)
from app.integrations.linkedin import LinkedInProvider
from app.integrations.registry import mapeamento_padrao
from app.integrations.tiktok import TikTokProvider

CREDS = {"access_token": "tok", "expires_at": 9e12, "scopes": ["r_ads", "r_ads_reporting"]}


def test_janelas_cobrem_o_periodo_sem_sobrepor() -> None:
    js = list(janelas(date(2026, 1, 1), date(2026, 3, 1), 30))
    assert js[0] == (date(2026, 1, 1), date(2026, 1, 30))
    assert js[-1][1] == date(2026, 3, 1)
    assert all(b < c for (_, b), (c, _) in zip(js, js[1:], strict=False))


# --- LinkedIn ----------------------------------------------------------------


@respx.mock
def test_linkedin_troca_codigo_e_exige_escopos() -> None:
    respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(
        return_value=httpx.Response(
            200,
            json={"access_token": "a", "expires_in": 100, "refresh_token": "r", "scope": "r_ads"},
        )
    )
    with pytest.raises(PermissionProviderError):
        LinkedInProvider().exchange_code("c", "")


@respx.mock
def test_linkedin_troca_codigo_ok() -> None:
    respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "a",
                "expires_in": 100,
                "refresh_token": "r",
                "scope": "r_ads,r_ads_reporting",
            },
        )
    )
    creds = LinkedInProvider().exchange_code("c", "")
    assert creds["refresh_token"] == "r" and creds["scopes"] == ["r_ads", "r_ads_reporting"]


@respx.mock
def test_linkedin_renova_token_expirado() -> None:
    rota = respx.post("https://www.linkedin.com/oauth/v2/accessToken").mock(
        return_value=httpx.Response(200, json={"access_token": "novo", "expires_in": 100})
    )
    novas = LinkedInProvider().ensure_fresh({**CREDS, "expires_at": 0, "refresh_token": "r"})
    assert novas and novas["access_token"] == "novo" and novas["refresh_token"] == "r"
    assert "grant_type=refresh_token" in rota.calls.last.request.content.decode()
    with pytest.raises(PermissionProviderError):
        LinkedInProvider().ensure_fresh({**CREDS, "expires_at": 0})


@respx.mock
def test_linkedin_lista_contas_paginando() -> None:
    rota = respx.get(url__startswith="https://api.linkedin.com/rest/adAccounts").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "elements": [{"id": 1, "name": "Conta A", "currency": "BRL"}],
                    "metadata": {"nextPageToken": "p2"},
                },
            ),
            httpx.Response(
                200, json={"elements": [{"id": 2, "name": "Teste", "test": True}], "metadata": {}}
            ),
        ]
    )
    contas = LinkedInProvider().list_accounts(CREDS)
    assert [(c.id_externo, c.nome, c.moeda) for c in contas] == [("1", "Conta A", "BRL")]
    req = rota.calls.last.request
    assert req.headers["LinkedIn-Version"] and "pageToken=p2" in str(req.url)


@respx.mock
def test_linkedin_metricas_por_conjunto() -> None:
    respx.get(url__startswith="https://api.linkedin.com/rest/adAccounts/9/adCampaignGroups").mock(
        return_value=httpx.Response(200, json={"elements": [{"id": 10, "name": "Grupo"}]})
    )
    respx.get(url__startswith="https://api.linkedin.com/rest/adAccounts/9/adCampaigns").mock(
        return_value=httpx.Response(200, json={"elements": [{"id": 20, "name": "Campanha"}]})
    )
    analytics = respx.get(url__startswith="https://api.linkedin.com/rest/adAnalytics").mock(
        return_value=httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "dateRange": {"start": {"year": 2026, "month": 3, "day": 2}},
                        "pivotValues": [
                            "urn:li:sponsoredCampaignGroup:10",
                            "urn:li:sponsoredCampaign:20",
                        ],
                        "costInLocalCurrency": "12.5",
                        "impressions": 1000,
                        "clicks": 30,
                        "externalWebsiteConversions": 3,
                        "conversionValueInLocalCurrency": "90",
                    }
                ]
            },
        )
    )
    rows = list(
        LinkedInProvider().fetch_metrics(
            CREDS, "9", "conjunto", date(2026, 3, 1), date(2026, 3, 5), {}
        )
    )
    assert len(rows) == 1
    r = rows[0]
    assert (r.data, r.entidade_externa_id, r.entidade_nome) == (date(2026, 3, 2), "20", "Campanha")
    assert (r.campanha_externa_id, r.campanha_nome) == ("10", "Grupo")
    assert str(r.investimento) == "12.5" and r.impressoes == 1000 and r.cliques == 30
    conv, valor = aplicar_mapeamento(r.conversoes_detalhe, mapeamento_padrao("linkedin_ads"))
    assert conv == 3 and valor == 90
    url = unquote(str(analytics.calls.last.request.url))
    assert "pivots=List(CAMPAIGN_GROUP,CAMPAIGN)" in url
    assert "accounts=List(urn:li:sponsoredAccount:9)" in url
    assert "dateRange=(start:(year:2026,month:3,day:1),end:(year:2026,month:3,day:5))" in url


@respx.mock
def test_linkedin_classifica_erros() -> None:
    respx.get(url__startswith="https://api.linkedin.com/rest/adAccounts").mock(
        side_effect=[httpx.Response(429), httpx.Response(401)]
    )
    with pytest.raises(RetryableProviderError):
        LinkedInProvider().list_accounts(CREDS)
    with pytest.raises(PermissionProviderError):
        LinkedInProvider().list_accounts(CREDS)


# --- TikTok ------------------------------------------------------------------

TT = "https://business-api.tiktok.com/open_api/v1.3"


def test_tiktok_url_de_autorizacao() -> None:
    q = parse_qs(urlsplit(TikTokProvider().authorize_url("st", "")).query)
    assert q["app_id"] == ["tiktok-app"] and q["state"] == ["st"]


@respx.mock
def test_tiktok_troca_codigo() -> None:
    rota = respx.post(f"{TT}/oauth2/access_token/").mock(
        return_value=httpx.Response(
            200,
            json={"code": 0, "data": {"access_token": "a", "advertiser_ids": [1], "scope": [4]}},
        )
    )
    creds = TikTokProvider().exchange_code("c", "")
    assert creds == {"access_token": "a", "advertiser_ids": ["1"], "scopes": ["4"]}
    assert json.loads(rota.calls.last.request.content)["auth_code"] == "c"


@respx.mock
def test_tiktok_lista_contas_com_moeda_e_fuso() -> None:
    respx.get(f"{TT}/oauth2/advertiser/get/").mock(
        return_value=httpx.Response(
            200,
            json={"code": 0, "data": {"list": [{"advertiser_id": 7, "advertiser_name": "A"}]}},
        )
    )
    info = respx.get(f"{TT}/advertiser/info/").mock(
        return_value=httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "list": [
                        {
                            "advertiser_id": 7,
                            "name": "Anunciante",
                            "currency": "BRL",
                            "timezone": "America/Sao_Paulo",
                        }
                    ]
                },
            },
        )
    )
    [c] = TikTokProvider().list_accounts({"access_token": "tok"})
    assert (c.id_externo, c.nome, c.moeda, c.fuso) == (
        "7",
        "Anunciante",
        "BRL",
        "America/Sao_Paulo",
    )
    assert info.calls.last.request.headers["Access-Token"] == "tok"


@respx.mock
def test_tiktok_metricas_paginam_e_dividem_periodo() -> None:
    def linha(dia: str) -> dict[str, object]:
        return {
            "dimensions": {"ad_id": "3", "stat_time_day": f"{dia} 00:00:00"},
            "metrics": {
                "spend": "10.00",
                "impressions": "500",
                "clicks": "20",
                "conversion": "2",
                "complete_payment": "1",
                "total_complete_payment_rate": "150.00",
                "campaign_id": "1",
                "campaign_name": "Camp",
                "adgroup_id": "2",
                "adgroup_name": "Grupo",
                "ad_name": "Anúncio",
            },
        }

    rota = respx.get(f"{TT}/report/integrated/get/").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"list": [linha("2026-01-01")], "page_info": {"total_page": 2}},
                },
            ),
            httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"list": [linha("2026-01-02")], "page_info": {"total_page": 2}},
                },
            ),
            httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"list": [linha("2026-02-05")], "page_info": {"total_page": 1}},
                },
            ),
        ]
    )
    rows = list(
        TikTokProvider().fetch_metrics(
            {"access_token": "tok"}, "7", "anuncio", date(2026, 1, 1), date(2026, 2, 5), {}
        )
    )
    assert [r.data for r in rows] == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 2, 5)]
    r = rows[0]
    assert (r.entidade_externa_id, r.entidade_nome, r.campanha_externa_id) == ("3", "Anúncio", "1")
    assert (r.conjunto_externo_id, r.conjunto_nome) == ("2", "Grupo")
    conv, _ = aplicar_mapeamento(r.conversoes_detalhe, mapeamento_padrao("tiktok_ads"))
    assert conv == 2
    _, valor = aplicar_mapeamento(r.conversoes_detalhe, {"action_types": ["complete_payment"]})
    assert valor == 150
    params = parse_qs(urlsplit(str(rota.calls[2].request.url)).query)
    assert params["start_date"] == ["2026-01-31"] and params["end_date"] == ["2026-02-05"]


@respx.mock
def test_tiktok_classifica_erros_do_envelope() -> None:
    respx.get(f"{TT}/oauth2/advertiser/get/").mock(
        side_effect=[
            httpx.Response(200, json={"code": 40100, "message": "QPS"}),
            httpx.Response(200, json={"code": 40105, "message": "token inválido"}),
        ]
    )
    with pytest.raises(RetryableProviderError):
        TikTokProvider().list_accounts({"access_token": "tok"})
    with pytest.raises(PermissionProviderError):
        TikTokProvider().list_accounts({"access_token": "tok"})
