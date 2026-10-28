"""Login interno via Google (OIDC Authorization Code + PKCE)."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.core.chaves import config_efetiva
from app.core.config import get_settings


class OIDCError(Exception):
    pass


@dataclass
class IdentidadeGoogle:
    sub: str
    email: str
    nome: str | None


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def login_redirect_uri() -> str:
    return f"{get_settings().api_v1_url}/auth/google/callback"


def build_authorize_url(state: str, nonce: str, code_verifier: str) -> str:
    s = config_efetiva()
    params = {
        "client_id": s.google_oidc_client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": login_redirect_uri(),
        "state": state,
        "nonce": nonce,
        "code_challenge": pkce_challenge(code_verifier),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{s.google_oidc_authorize_url}?{urlencode(params)}"


def exchange_code(code: str, code_verifier: str) -> dict[str, Any]:
    s = config_efetiva()
    try:
        resp = httpx.post(
            s.google_oidc_token_url,
            data={
                "code": code,
                "client_id": s.google_oidc_client_id,
                "client_secret": s.google_oidc_client_secret,
                "redirect_uri": login_redirect_uri(),
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise OIDCError("falha de rede na troca do código") from exc
    if resp.status_code != 200:
        raise OIDCError(f"troca do código recusada ({resp.status_code})")
    data: dict[str, Any] = resp.json()
    if "id_token" not in data:
        raise OIDCError("resposta sem id_token")
    return data


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=3600)


def verify_id_token(id_token: str, nonce: str) -> IdentidadeGoogle:
    """Valida assinatura (JWKS), issuer, audience, exp, nonce e email_verified."""
    s = config_efetiva()
    try:
        key = _jwks_client(s.google_oidc_jwks_url).get_signing_key_from_jwt(id_token)
        claims: dict[str, Any] = jwt.decode(
            id_token,
            key.key,
            algorithms=["RS256"],
            audience=s.google_oidc_client_id,
            issuer=_issuers(s.google_oidc_issuer),
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            leeway=60,
        )
    except jwt.PyJWTError as exc:
        raise OIDCError(f"id_token inválido: {exc.__class__.__name__}") from exc
    if claims.get("nonce") != nonce:
        raise OIDCError("nonce divergente")
    if claims.get("email_verified") is not True:
        raise OIDCError("e-mail não verificado")
    email = claims.get("email")
    if not isinstance(email, str) or not email:
        raise OIDCError("id_token sem e-mail")
    return IdentidadeGoogle(
        sub=str(claims["sub"]), email=normalize_email(email), nome=claims.get("name")
    )


def _issuers(issuer: str) -> list[str] | str:
    # O Google emite tokens com e sem esquema.
    if issuer == "https://accounts.google.com":
        return ["https://accounts.google.com", "accounts.google.com"]
    return issuer


def normalize_email(email: str) -> str:
    return email.strip().lower()
