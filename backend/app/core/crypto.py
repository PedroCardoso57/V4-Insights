"""Armazenamento criptografado de credenciais de integrações."""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import CredencialIntegracao

_PREFIX = "secret:"


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def _fernet() -> MultiFernet:
    """Cifra com a chave atual; decifra também com as anteriores (rotação sem downtime)."""
    s = get_settings()
    chaves = [s.encryption_key, *s.encryption_keys_previous]
    return MultiFernet([Fernet(k.encode()) for k in chaves])


def rotacionar_chaves(db: Session) -> int:
    """Recifra todas as credenciais com a chave atual. Retorna quantas foram regravadas."""
    mf = _fernet()
    n = 0
    for cred in db.scalars(select(CredencialIntegracao)):
        cred.ciphertext = mf.rotate(cred.ciphertext)
        n += 1
    db.commit()
    return n


def store_secret(
    db: Session,
    data: dict[str, Any],
    reference: str | None = None,
    integracao_id: uuid.UUID | None = None,
) -> str:
    """Grava (ou substitui) credenciais criptografadas e devolve a referência opaca."""
    ciphertext = _fernet().encrypt(json.dumps(data).encode())
    if reference:
        segredo = db.get(CredencialIntegracao, _parse(reference))
        if segredo is not None:
            segredo.ciphertext = ciphertext
            return reference
    segredo = CredencialIntegracao(
        id=uuid.uuid4(), ciphertext=ciphertext, integracao_id=integracao_id
    )
    db.add(segredo)
    db.flush()
    return f"{_PREFIX}{segredo.id}"


def load_secret(db: Session, reference: str) -> dict[str, Any]:
    segredo = db.get(CredencialIntegracao, _parse(reference))
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
    segredo = db.get(CredencialIntegracao, _parse(reference))
    if segredo is not None:
        db.delete(segredo)


def _parse(reference: str) -> uuid.UUID:
    if not reference.startswith(_PREFIX):
        raise ValueError("referência de credencial inválida")
    return uuid.UUID(reference[len(_PREFIX) :])
