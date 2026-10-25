from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import GERENCIA, Principal, require_roles
from app.api.rbac import carteira_subquery, get_cliente_autorizado
from app.db.session import get_db
from app.models import Auditoria
from app.schemas import AuditoriaOut, Page

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("", response_model=Page[AuditoriaOut])
def listar(
    cliente_id: uuid.UUID | None = None,
    entidade: str | None = Query(default=None, max_length=60),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(require_roles(*GERENCIA)),
    db: Session = Depends(get_db),
) -> Page[AuditoriaOut]:
    stmt = select(Auditoria)
    if not principal.is_admin:
        # Gestor: apenas eventos de clientes da própria carteira.
        stmt = stmt.where(Auditoria.cliente_id.in_(carteira_subquery(principal)))
    if cliente_id:
        get_cliente_autorizado(db, principal, cliente_id)
        stmt = stmt.where(Auditoria.cliente_id == cliente_id)
    if entidade:
        stmt = stmt.where(Auditoria.entidade == entidade)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Auditoria.data_hora.desc(), Auditoria.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[AuditoriaOut.model_validate(a) for a in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
