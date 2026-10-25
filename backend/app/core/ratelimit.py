"""Rate limit por janela fixa no Redis (SPEC-07: login e endpoints caros)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Literal

from fastapi import Depends, Request

from app.api.deps import Principal, get_principal
from app.api.errors import AppError
from app.core.config import get_settings
from app.core.sessions import client_ip
from app.workers.queue import get_redis

log = logging.getLogger(__name__)


def _parse(regra: str) -> tuple[int, int] | None:
    if not regra:
        return None
    limite, janela = regra.split("/", 1)
    return int(limite), int(janela)


def verificar(chave: str, regra: str) -> None:
    """Conta a requisição e levanta 429 ao exceder `limite` na janela."""
    parsed = _parse(regra)
    if parsed is None:
        return
    limite, janela = parsed
    bucket = int(time.time() // janela)
    k = f"v4:rl:{chave}:{bucket}"
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(k)
        pipe.expire(k, janela + 1)
        atual = int(pipe.execute()[0])
    except Exception as exc:  # Redis fora: não bloqueia o acesso (readiness já alerta)
        log.warning("rate limit indisponível: %s", exc.__class__.__name__)
        return
    if atual > limite:
        restante = janela - int(time.time()) % janela
        raise AppError(
            429,
            "Muitas requisições. Tente novamente em instantes.",
            headers={"Retry-After": str(restante)},
        )


def por_ip(nome: str, regra: Callable[[], str]) -> Callable[[Request], None]:
    def _dep(request: Request) -> None:
        verificar(f"{nome}:ip:{client_ip(request) or '-'}", regra())

    return _dep


def por_usuario(nome: str, regra: Callable[[], str]) -> Callable[..., Principal]:
    def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        verificar(f"{nome}:u:{principal.usuario.id}", regra())
        return principal

    return _dep


Tipo = Literal["login", "login_email", "caro"]


def regra(tipo: Tipo) -> Callable[[], str]:
    s = get_settings
    if tipo == "login":
        return lambda: s().rate_limit_login
    if tipo == "login_email":
        return lambda: s().rate_limit_login_email
    return lambda: s().rate_limit_operacoes_caras
