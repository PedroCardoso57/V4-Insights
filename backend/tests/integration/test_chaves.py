"""Chaves dos apps das plataformas cadastradas pela tela de Configurações."""

from __future__ import annotations

from sqlalchemy import select

from app.core import chaves, oidc
from app.integrations.base import ConfigProviderError
from app.integrations.google_ads import GoogleAdsProvider
from app.integrations.meta import MetaProvider
from app.models import Auditoria, ChavePlataforma


def _grupo(resposta, gid):  # type: ignore[no-untyped-def]
    return next(g for g in resposta if g["id"] == gid)


def _campo(grupo, chave):  # type: ignore[no-untyped-def]
    return next(c for c in grupo["campos"] if c["chave"] == chave)


def test_admin_cadastra_chaves_e_provedor_passa_a_usar(factory, db) -> None:
    admin = factory.login(factory.usuario("admin"))
    gads = _grupo(admin.get("/configuracoes/chaves").json(), "google_ads")
    assert gads["configurado"] is False  # nada no ambiente de testes
    assert gads["redirect_uri"].endswith("/api/v1/integracoes/google_ads/callback")
    try:
        GoogleAdsProvider()
        raise AssertionError("Google Ads não deveria estar configurado")
    except ConfigProviderError:
        pass

    valores = {
        "google_ads_client_id": " 123.apps ",
        "google_ads_client_secret": "segredo-gads",
        "google_ads_developer_token": "token-dev",
    }
    r = admin.put("/configuracoes/chaves", json={"valores": valores})
    assert r.status_code == 200, r.text
    gads = _grupo(r.json(), "google_ads")
    assert gads["configurado"] is True  # o MCC é opcional
    client_id = _campo(gads, "google_ads_client_id")
    assert client_id["origem"] == "sistema" and client_id["valor"] == "123.apps"
    segredo = _campo(gads, "google_ads_client_secret")
    assert segredo["origem"] == "sistema" and segredo["valor"] is None
    assert "segredo-gads" not in r.text and "token-dev" not in r.text

    # cifrado no banco, nunca em texto puro nem na auditoria
    row = db.get(ChavePlataforma, "google_ads_client_secret")
    assert row is not None and b"segredo-gads" not in row.ciphertext
    log = db.scalar(select(Auditoria).where(Auditoria.acao == "alterar_chaves"))
    assert log is not None and sorted(log.metadados["chaves"]) == sorted(valores)
    assert "segredo-gads" not in str(log.metadados)

    p = GoogleAdsProvider()
    assert p.client_id == "123.apps" and p.client_secret == "segredo-gads"

    # vazio remove a chave cadastrada: volta a valer o .env (aqui, nada)
    r = admin.put("/configuracoes/chaves", json={"valores": {"google_ads_client_secret": ""}})
    gads = _grupo(r.json(), "google_ads")
    assert gads["configurado"] is False
    assert _campo(gads, "google_ads_client_secret")["origem"] is None
    db.expire_all()
    assert db.get(ChavePlataforma, "google_ads_client_secret") is None


def test_chave_cadastrada_tem_prioridade_sobre_env(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    meta = _grupo(admin.get("/configuracoes/chaves").json(), "meta_ads")
    assert _campo(meta, "meta_app_id")["origem"] == "env"
    admin.put("/configuracoes/chaves", json={"valores": {"meta_app_id": "do-sistema"}})
    assert MetaProvider().app_id == "do-sistema"


def test_login_google_usa_chave_cadastrada_e_mostra_origem_env(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    google = _grupo(admin.get("/configuracoes/chaves").json(), "google_login")
    # nos testes o client id vem do ambiente
    assert _campo(google, "google_oidc_client_id")["origem"] == "env"
    admin.put("/configuracoes/chaves", json={"valores": {"google_oidc_client_id": "novo-id"}})
    assert "client_id=novo-id" in oidc.build_authorize_url("s", "n", "v")
    assert chaves.config_efetiva().google_oidc_client_id == "novo-id"


def test_somente_admin_e_chaves_conhecidas(factory) -> None:
    gestor = factory.login(factory.usuario("gestor"))
    assert gestor.get("/configuracoes/chaves").status_code == 403
    body = {"valores": {"meta_app_id": "1"}}
    assert gestor.put("/configuracoes/chaves", json=body).status_code == 403
    admin = factory.login(factory.usuario("admin"))
    r = admin.put("/configuracoes/chaves", json={"valores": {"database_url": "x"}})
    assert r.status_code == 422
    r = admin.put("/configuracoes/chaves", json={"valores": {"meta_app_id": "x" * 501}})
    assert r.status_code == 422
