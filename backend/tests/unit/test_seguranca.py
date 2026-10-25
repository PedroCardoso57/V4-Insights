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


def test_hash_de_senha_argon2id_e_verificacao() -> None:
    from app.core import senhas

    h = senhas.gerar_hash("Uma-senha-boa-1")
    assert h.startswith("$argon2id$") and "Uma-senha-boa-1" not in h
    assert senhas.verificar(h, "Uma-senha-boa-1")
    assert not senhas.verificar(h, "outra-senha-qualquer")
    assert not senhas.verificar(None, "Uma-senha-boa-1")  # usuário sem senha nunca autentica
    assert not senhas.verificar("lixo", "x")


def test_politica_de_senha() -> None:
    import pytest

    from app.core import senhas

    for ruim in ("curta", " " * 12, "a" * 129, "maria.silva"):
        with pytest.raises(senhas.SenhaFraca):
            senhas.validar_politica(ruim, "maria.silva@v4.com")
    senhas.validar_politica("frase longa e boa", "maria.silva@v4.com")
