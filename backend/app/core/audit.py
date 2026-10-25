from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.sessions import client_ip
from app.models import Auditoria


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
    db.add(
        Auditoria(
            usuario_id=usuario_id,
            acao=acao,
            entidade=entidade,
            entidade_id=str(entidade_id) if entidade_id is not None else None,
            cliente_id=cliente_id,
            dados=dados or {},
            ip=client_ip(request) if request else None,
        )
    )
