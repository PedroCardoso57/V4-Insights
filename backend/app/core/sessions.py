"""Sessões de servidor, cookies e proteção CSRF."""

from __future__ import annotations

import hmac
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.crypto import random_token, sha256_hex
from app.models import Sessao

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def now() -> datetime:
    return datetime.now(UTC)


def create_session(db: Session, usuario_id: uuid.UUID, request: Request) -> tuple[str, Sessao]:
    settings = get_settings()
    token = random_token(32)
    sessao = Sessao(
        id=sha256_hex(token),
        usuario_id=usuario_id,
        csrf_token=random_token(24),
        expira_em=now() + timedelta(hours=settings.session_ttl_hours),
        ip=client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:400],
    )
    db.add(sessao)
    return token, sessao


def set_session_cookies(response: Response, token: str, sessao: Sessao) -> None:
    settings = get_settings()
    max_age = settings.session_ttl_hours * 3600
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
        sessao.csrf_token,
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
    sessao = db.get(Sessao, sha256_hex(token))
    if sessao is None or sessao.revogada_em is not None or sessao.expira_em <= now():
        return None
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
    return bool(header) and hmac.compare_digest(header, sessao.csrf_token)


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else None
