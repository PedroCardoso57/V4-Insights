from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Papel, Perfil


def perfil_id(db: Session, papel: Papel | str) -> uuid.UUID:
    """Resolve o id do perfil (tabela `perfis` da baseline) pelo código do papel."""
    pid = db.scalar(select(Perfil.id).where(Perfil.codigo == str(papel)))
    if pid is None:
        raise LookupError(f"perfil {papel} ausente — a baseline foi aplicada?")
    return pid
