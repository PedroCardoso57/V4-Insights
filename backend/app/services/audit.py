from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.context import current_request_id
from app.core.sessions import client_ip
from app.models import Auditoria


def _as_uuid(v: Any) -> uuid.UUID | None:
    if v is None or isinstance(v, uuid.UUID):
        return v
    try:
        return uuid.UUID(str(v))
    except ValueError:
        return None


def registrar(
    db: Session,
    *,
    usuario_id: uuid.UUID | None,
    acao: str,
    entidade: str,
    entidade_id: Any = None,
    cliente_id: uuid.UUID | None = None,
    dados: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """Registra ação sensível. `dados` nunca deve conter tokens ou segredos."""
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            acao=acao,
            entidade=entidade,
            entidade_id=_as_uuid(entidade_id),
            cliente_id=cliente_id,
            metadados=jsonable_encoder(dados or {}),
            ip=client_ip(request) if request else None,
            request_id=current_request_id(),
        )
    )
