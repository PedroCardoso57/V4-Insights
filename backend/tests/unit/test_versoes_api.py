"""M01: versões das APIs das plataformas e aviso antes do desligamento."""

from __future__ import annotations

from datetime import date

import pytest
from cryptography.fernet import Fernet

from app.core import versoes_api


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("", "v25.0"),
        (None, "v25.0"),
        ("v21.0", "v25.0"),
        ("v23.0", "v25.0"),
        ("v24.0", "v24.0"),
        ("v26.0", "v26.0"),
    ],
)
def test_meta_cai_na_padrao_quando_antiga(valor: str | None, esperado: str) -> None:
    assert versoes_api.meta_versao_ativa(valor) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("", "202609"),
        ("202410", "202609"),
        ("202511", "202609"),
        ("202512", "202512"),
        ("202610", "202610"),
    ],
)
def test_linkedin_cai_na_padrao_depois_de_12_meses(valor: str, esperado: str) -> None:
    assert versoes_api.linkedin_versao_ativa(valor, hoje=date(2026, 11, 11)) == esperado


def test_linkedin_desligamento_um_ano_depois() -> None:
    assert versoes_api.linkedin_desligamento("202609") == date(2027, 9, 1)
    assert versoes_api.linkedin_desligamento("202612") == date(2027, 12, 1)
    assert versoes_api.linkedin_desligamento("latest") is None


def test_env_antigo_vira_versoes_ativas(monkeypatch: pytest.MonkeyPatch) -> None:
    # .env gerados do exemplo antigo trazem versões que as plataformas já desligaram.
    from app.core.config import Settings

    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("META_GRAPH_VERSION", "v21.0")
    monkeypatch.setenv("GOOGLE_ADS_API_VERSION", "v18")
    monkeypatch.setenv("LINKEDIN_API_VERSION", "202410")
    monkeypatch.setenv("TIKTOK_API_VERSION", "")
    s = Settings()
    assert s.meta_graph_version == versoes_api.META_GRAPH_VERSION_PADRAO
    assert s.google_ads_api_version == versoes_api.GOOGLE_ADS_API_VERSION_PADRAO
    assert s.linkedin_api_version == versoes_api.LINKEDIN_API_VERSION_PADRAO
    assert s.tiktok_api_version == "v1.3"


def test_aviso_de_versao_perto_de_desligar() -> None:
    from app.services.alertas import versoes_api_vencendo

    # Google Ads v25 desliga em 01/08/2027: 59 dias antes já avisa, 61 não.
    perto = versoes_api_vencendo(hoje=date(2027, 6, 3))
    assert any("google_ads" in a and "v25" in a for a in perto)
    assert not any("google_ads" in a for a in versoes_api_vencendo(hoje=date(2027, 6, 1)))
    depois = versoes_api_vencendo(hoje=date(2027, 8, 2))
    assert any("google_ads" in a and "já foi desligada" in a for a in depois)


def test_linkedin_426_nao_repete() -> None:
    import httpx

    from app.integrations.base import ProviderError, RetryableProviderError, raise_for_response

    resp = httpx.Response(426, text='{"code":"NONEXISTENT_VERSION"}')
    with pytest.raises(ProviderError) as exc:
        raise_for_response(resp)
    assert not isinstance(exc.value, RetryableProviderError)
    assert "versão da API desligada" in str(exc.value)
