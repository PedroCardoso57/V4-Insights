"""SPEC-08: contratos comuns de lista, erro, paginação e serialização."""

from __future__ import annotations

import re
from datetime import datetime

import pytest

# ISO 8601 com designador de fuso: "Z" (UTC) ou ±hh:mm.
ISO_OFFSET = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


def _erro(resp, status: int, code: str) -> dict:  # type: ignore[no-untyped-def]
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert set(body) == {"error"}
    err = body["error"]
    assert err["code"] == code and err["message"]
    assert err["request_id"] == resp.headers["x-request-id"]
    return err


def test_envelopes_de_erro(anon, factory) -> None:
    _erro(anon.get("/clientes"), 401, "UNAUTHENTICATED")
    vis = factory.login(factory.usuario("visualizador"))
    _erro(vis.post("/clientes", json={"nome": "Nope"}), 403, "FORBIDDEN")
    _erro(vis.get("/clientes/00000000-0000-0000-0000-000000000000"), 404, "NOT_FOUND")
    admin = factory.login(factory.usuario("admin"))
    err = _erro(admin.post("/clientes", json={"nome": ""}), 422, "VALIDATION_ERROR")
    assert err["details"][0]["loc"][-1] == "nome"
    admin.post("/usuarios", json={"nome": "Bia", "email": "b@v4.com", "papel": "analista"})
    _erro(
        admin.post("/usuarios", json={"nome": "Bia", "email": "b@v4.com", "papel": "analista"}),
        409,
        "CONFLICT",
    )


def test_request_id_propagado(anon) -> None:
    r = anon.get("/health/live", headers={"X-Request-ID": "abc12345-req"})
    assert r.headers["x-request-id"] == "abc12345-req"
    r = anon.get("/health/live", headers={"X-Request-ID": "bad id!"})
    assert r.headers["x-request-id"] != "bad id!"


def test_lista_padrao_e_limite_de_pagina(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    for path in (
        "/clientes",
        "/usuarios",
        "/integracoes",
        "/dashboards",
        "/relatorios",
        "/auditoria",
    ):
        body = admin.get(path).json()
        assert set(body) == {"items", "page", "page_size", "total"}, path
        assert admin.get(f"{path}?page_size=101").status_code == 422, path


def test_timestamps_com_offset_e_dinheiro_string(factory) -> None:
    admin = factory.login(factory.usuario("admin"))
    c = admin.post("/clientes", json={"nome": "Cliente X"}).json()
    assert ISO_OFFSET.match(c["criado_em"]), c["criado_em"]
    assert datetime.fromisoformat(c["criado_em"]).tzinfo is not None
    r = admin.get(f"/clientes/{c['id']}/metricas/resumo").json()
    assert isinstance(r["atual"]["investimento"], str)


@pytest.mark.parametrize("papel", ["analista", "gestor", "visualizador"])
def test_nenhum_endpoint_lista_dados_de_outro_cliente(factory, papel) -> None:
    dono = factory.usuario("analista")
    alheio = factory.cliente("Alheio", membros=(dono,))
    da = factory.login(dono)
    da.post("/dashboards", json={"cliente_id": str(alheio.id), "nome": "D"})
    da.post("/relatorios", json={"cliente_id": str(alheio.id), "titulo": "Rel"})
    outro = factory.login(factory.usuario(papel))
    for path in ("/clientes", "/dashboards", "/relatorios"):
        assert outro.get(path).json()["items"] == [], path
    for path in (
        f"/clientes/{alheio.id}",
        f"/clientes/{alheio.id}/usuarios",
        f"/clientes/{alheio.id}/metricas/resumo",
        f"/clientes/{alheio.id}/campanhas",
        f"/dashboards?cliente_id={alheio.id}",
    ):
        r = outro.get(path)
        assert r.status_code == 404 or r.json().get("items") == [], path


def test_openapi_documenta_erros_e_enums(anon) -> None:
    spec = anon.get("/openapi.json").json()
    assert "/api/v1/relatorios/{relatorio_id}/gerar" in spec["paths"]
    schemas = spec["components"]["schemas"]
    assert "ErrorResponse" in schemas
    assert set(schemas["Plataforma"]["enum"]) == {
        "meta_ads",
        "google_ads",
        "linkedin_ads",
        "tiktok_ads",
    }
    get_cli = spec["paths"]["/api/v1/clientes"]["get"]
    assert "403" in get_cli["responses"] and "422" in get_cli["responses"]
