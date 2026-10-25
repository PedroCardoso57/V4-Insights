"""Proteção contra SSRF em URLs externas seguidas pelo sistema (SPEC-07).

Só URLs HTTPS para hosts explicitamente permitidos, sem credenciais embutidas nem portas
alternativas, são acessadas — mesmo quando a URL vem da resposta de um provedor
(ex.: `paging.next` da Graph API).
"""

from __future__ import annotations

from urllib.parse import urlsplit


class UrlNaoPermitida(ValueError):
    pass


def exigir_url_permitida(url: str, hosts: frozenset[str] | set[str]) -> str:
    try:
        partes = urlsplit(url)
        porta = partes.port
    except ValueError as exc:
        raise UrlNaoPermitida("URL malformada") from exc
    if partes.scheme != "https":
        raise UrlNaoPermitida("apenas https é permitido")
    if partes.username or partes.password:
        raise UrlNaoPermitida("credenciais embutidas na URL")
    if porta not in (None, 443):
        raise UrlNaoPermitida("porta não permitida")
    host = (partes.hostname or "").lower().rstrip(".")
    if host not in hosts:
        raise UrlNaoPermitida(f"host não permitido: {host or '(vazio)'}")
    return url
