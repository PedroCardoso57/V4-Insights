from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, MultiFernet

from app.core.urls import UrlNaoPermitida, exigir_url_permitida

HOSTS = frozenset({"graph.facebook.com"})


@pytest.mark.parametrize(
    "url",
    [
        "http://graph.facebook.com/v21.0/act_1/insights",  # sem TLS
        "https://169.254.169.254/latest/meta-data",  # metadados da nuvem
        "https://graph.facebook.com.evil.example/x",  # sufixo enganoso
        "https://user:pass@graph.facebook.com/x",  # credenciais embutidas
        "https://graph.facebook.com:8443/x",  # porta alternativa
        "https://localhost/x",
        "file:///etc/passwd",
    ],
)
def test_ssrf_bloqueia_urls_fora_da_lista(url: str) -> None:
    with pytest.raises(UrlNaoPermitida):
        exigir_url_permitida(url, HOSTS)


def test_ssrf_permite_host_oficial() -> None:
    url = "https://graph.facebook.com/v21.0/act_1/insights?after=abc"
    assert exigir_url_permitida(url, HOSTS) == url


def test_multifernet_decifra_chave_antiga() -> None:
    antiga, nova = Fernet.generate_key(), Fernet.generate_key()
    token = Fernet(antiga).encrypt(b"segredo")
    mf = MultiFernet([Fernet(nova), Fernet(antiga)])
    rotacionado = mf.rotate(token)
    assert Fernet(nova).decrypt(rotacionado) == b"segredo"
