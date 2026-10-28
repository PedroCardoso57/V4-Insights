"""Chaves dos apps das plataformas: banco (tela de Configurações) com fallback no `.env`.

Os provedores e o login Google leem a configuração por `config_efetiva()`, que sobrepõe às
variáveis de ambiente os valores cadastrados pelo admin. Os valores ficam cifrados com a
ENCRYPTION_KEY; segredos nunca voltam para a tela, só a indicação de que existem.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.crypto import cifrar, decifrar
from app.models import ChavePlataforma


@dataclass(frozen=True)
class Campo:
    chave: str
    rotulo: str
    secreto: bool = False
    obrigatorio: bool = True


@dataclass(frozen=True)
class Grupo:
    id: str
    nome: str
    callback: str  # caminho do redirect URI, relativo a /api/v1
    campos: tuple[Campo, ...]


GRUPOS: tuple[Grupo, ...] = (
    Grupo(
        "google_login",
        "Login com Google",
        "/auth/google/callback",
        (
            Campo("google_oidc_client_id", "ID do cliente"),
            Campo("google_oidc_client_secret", "Chave secreta do cliente", secreto=True),
        ),
    ),
    Grupo(
        "meta_ads",
        "Meta Ads",
        "/integracoes/meta_ads/callback",
        (
            Campo("meta_app_id", "ID do app"),
            Campo("meta_app_secret", "Chave secreta do app", secreto=True),
        ),
    ),
    Grupo(
        "google_ads",
        "Google Ads",
        "/integracoes/google_ads/callback",
        (
            Campo("google_ads_client_id", "ID do cliente OAuth"),
            Campo("google_ads_client_secret", "Chave secreta do cliente", secreto=True),
            Campo("google_ads_developer_token", "Developer token", secreto=True),
            Campo(
                "google_ads_login_customer_id",
                "ID da conta gerenciadora (MCC)",
                obrigatorio=False,
            ),
        ),
    ),
    Grupo(
        "linkedin_ads",
        "LinkedIn Ads",
        "/integracoes/linkedin_ads/callback",
        (
            Campo("linkedin_client_id", "Client ID"),
            Campo("linkedin_client_secret", "Client secret", secreto=True),
        ),
    ),
    Grupo(
        "tiktok_ads",
        "TikTok Ads",
        "/integracoes/tiktok_ads/callback",
        (
            Campo("tiktok_app_id", "App ID"),
            Campo("tiktok_app_secret", "Secret", secreto=True),
        ),
    ),
)
CAMPOS: dict[str, Campo] = {c.chave: c for g in GRUPOS for c in g.campos}

# Cache curto por processo: a API invalida ao salvar; o worker vê a mudança em até TTL.
_TTL = 30.0
_lock = threading.Lock()
_cache: tuple[float, dict[str, str]] | None = None


def limpar_cache() -> None:
    global _cache
    with _lock:
        _cache = None


def _ler_banco() -> dict[str, str]:
    from app.db.session import get_sessionmaker

    db = get_sessionmaker()()
    try:
        valores: dict[str, str] = {}
        for row in db.scalars(select(ChavePlataforma)):
            if row.chave not in CAMPOS:
                continue
            try:
                valores[row.chave] = decifrar(row.ciphertext)
            except ValueError:
                continue  # cifrado com chave que não está mais configurada: vale o .env
        return valores
    finally:
        db.close()


def valores_banco() -> dict[str, str]:
    """Valores cadastrados pela tela (decifrados). Banco indisponível → nenhum."""
    global _cache
    with _lock:
        if _cache is not None and time.monotonic() - _cache[0] < _TTL:
            return _cache[1]
    try:
        valores = _ler_banco()
    except SQLAlchemyError:
        valores = {}
    with _lock:
        _cache = (time.monotonic(), valores)
    return valores


def config_efetiva() -> Settings:
    """Settings do ambiente com as chaves cadastradas na tela por cima."""
    base = get_settings()
    valores = valores_banco()
    return base.model_copy(update=valores) if valores else base


def salvar(db: Session, valores: dict[str, str | None], usuario_id: uuid.UUID) -> list[str]:
    """Grava (texto) ou remove (vazio/None → volta a valer o `.env`). Devolve as chaves
    alteradas. O chamador faz o commit e chama `limpar_cache()`."""
    alteradas: list[str] = []
    for chave, valor in valores.items():
        if chave not in CAMPOS:
            raise KeyError(chave)
        atual = db.get(ChavePlataforma, chave)
        valor = (valor or "").strip()
        if not valor:
            if atual is not None:
                db.delete(atual)
                alteradas.append(chave)
            continue
        if atual is None:
            db.add(
                ChavePlataforma(chave=chave, ciphertext=cifrar(valor), atualizado_por=usuario_id)
            )
        else:
            atual.ciphertext = cifrar(valor)
            atual.atualizado_por = usuario_id
        alteradas.append(chave)
    return alteradas
