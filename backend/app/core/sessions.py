"""Sessões de servidor, cookies e proteção CSRF."""

from __future__ import annotations

import hmac
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.crypto import random_token, sha256_hex
from app.models import Sessao

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def now() -> datetime:
    return datetime.now(UTC)


def create_session(db: Session, usuario_id: uuid.UUID, request: Request) -> tuple[str, str, Sessao]:
    """Cria a sessão e devolve (token, csrf_token, sessao). Só os hashes são persistidos."""
    settings = get_settings()
    token = random_token(32)
    csrf = random_token(24)
    sessao = Sessao(
        token_hash=sha256_hex(token),
        csrf_hash=sha256_hex(csrf),
        usuario_id=usuario_id,
        expira_em=now() + timedelta(hours=settings.session_ttl_hours),
        ip=client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:400],
    )
    db.add(sessao)
    return token, csrf, sessao


def set_session_cookies(
    response: Response, token: str, csrf: str, *, persistente: bool = True
) -> None:
    """Grava os cookies. `persistente=False` gera cookies de sessão do navegador."""
    settings = get_settings()
    max_age = settings.session_ttl_hours * 3600 if persistente else None
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    # Cookie legível pelo frontend para o padrão double-submit (não é credencial).
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    for name in (settings.session_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(name, path="/", secure=settings.cookie_secure, samesite="lax")


def find_active_session(db: Session, token: str | None) -> Sessao | None:
    if not token:
        return None
    sessao = db.scalar(select(Sessao).where(Sessao.token_hash == sha256_hex(token)))
    if sessao is None or sessao.revogado_em is not None or sessao.expira_em <= now():
        return None
    # Atualiza o último acesso no máximo a cada 5 minutos (evita escrita a cada request).
    agora = now()
    if sessao.ultimo_acesso_em is None or agora - sessao.ultimo_acesso_em > timedelta(minutes=5):
        sessao.ultimo_acesso_em = agora
        db.commit()
    return sessao


def origin_allowed(request: Request) -> bool:
    allowed = set(get_settings().allowed_origins)
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/") in allowed
    referer = request.headers.get("referer")
    if referer:
        parts = urlsplit(referer)
        return f"{parts.scheme}://{parts.netloc}" in allowed
    return False


def csrf_valid(request: Request, sessao: Sessao) -> bool:
    header = request.headers.get("x-csrf-token", "")
    return bool(header) and hmac.compare_digest(sha256_hex(header), sessao.csrf_hash)


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None
