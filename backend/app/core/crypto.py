"""Armazenamento criptografado de credenciais de integrações."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Segredo

_PREFIX = "secret:"


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def _fernet() -> Fernet:
    return Fernet(get_settings().encryption_key.encode())


def store_secret(db: Session, data: dict[str, Any], reference: str | None = None) -> str:
    """Grava (ou substitui) um segredo e devolve a referência opaca."""
    ciphertext = _fernet().encrypt(json.dumps(data).encode())
    if reference:
        segredo = db.get(Segredo, _parse(reference))
        if segredo is not None:
            segredo.ciphertext = ciphertext
            return reference
    segredo = Segredo(id=uuid.uuid4(), ciphertext=ciphertext)
    db.add(segredo)
    db.flush()
    return f"{_PREFIX}{segredo.id}"


def load_secret(db: Session, reference: str) -> dict[str, Any]:
    segredo = db.get(Segredo, _parse(reference))
    if segredo is None:
        raise KeyError("segredo inexistente")
    try:
        data: dict[str, Any] = json.loads(_fernet().decrypt(segredo.ciphertext))
    except InvalidToken as exc:
        raise ValueError("falha ao descriptografar segredo") from exc
    return data


def delete_secret(db: Session, reference: str | None) -> None:
    if not reference:
        return
    segredo = db.get(Segredo, _parse(reference))
    if segredo is not None:
        db.delete(segredo)


def _parse(reference: str) -> uuid.UUID:
    if not reference.startswith(_PREFIX):
        raise ValueError("referência de credencial inválida")
    return uuid.UUID(reference[len(_PREFIX) :])
