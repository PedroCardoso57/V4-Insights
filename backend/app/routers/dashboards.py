from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import registrar
from app.core.deps import EDICAO, Principal, get_principal, require_roles
from app.core.rbac import get_cliente_autorizado, scope_clientes
from app.db import get_db
from app.models import Dashboard, Widget
from app.schemas import DashboardIn, DashboardOut, DashboardUpdate, WidgetIn, WidgetOut

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _get(db: Session, principal: Principal, dashboard_id: uuid.UUID) -> Dashboard:
    d = db.get(Dashboard, dashboard_id, options=[selectinload(Dashboard.widgets)])
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dashboard não encontrado")
    get_cliente_autorizado(db, principal, d.cliente_id)
    return d


@router.get("", response_model=list[DashboardOut])
def listar(
    cliente_id: uuid.UUID | None = None,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[DashboardOut]:
    stmt = scope_clientes(
        select(Dashboard).options(selectinload(Dashboard.widgets)), principal, Dashboard.cliente_id
    )
    if cliente_id:
        stmt = stmt.where(Dashboard.cliente_id == cliente_id)
    rows = db.scalars(stmt.order_by(Dashboard.nome, Dashboard.id)).all()
    return [DashboardOut.model_validate(d) for d in rows]


@router.post("", response_model=DashboardOut, status_code=201)
def criar(
    body: DashboardIn,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> DashboardOut:
    get_cliente_autorizado(db, principal, body.cliente_id)
    d = Dashboard(
        cliente_id=body.cliente_id,
        nome=body.nome,
        descricao=body.descricao,
        filtros=body.filtros,
        layout=body.layout,
        criado_por=principal.usuario.id,
    )
    db.add(d)
    db.flush()
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="criar",
        entidade="dashboard",
        entidade_id=d.id,
        cliente_id=d.cliente_id,
        request=request,
    )
    db.commit()
    return DashboardOut.model_validate(_get(db, principal, d.id))


@router.get("/{dashboard_id}", response_model=DashboardOut)
def obter(
    dashboard_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> DashboardOut:
    return DashboardOut.model_validate(_get(db, principal, dashboard_id))


@router.patch("/{dashboard_id}", response_model=DashboardOut)
def editar(
    dashboard_id: uuid.UUID,
    body: DashboardUpdate,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> DashboardOut:
    d = _get(db, principal, dashboard_id)
    dados = body.model_dump(exclude_unset=True, exclude={"widgets"})
    for k, v in dados.items():
        if k == "nome" and v is None:
            continue
        setattr(d, k, v)
    if body.widgets is not None:
        # Substitui o conjunto de widgets (edição do layout completo).
        d.widgets.clear()
        db.flush()
        for i, w in enumerate(body.widgets):
            d.widgets.append(_widget(w, i))
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="editar",
        entidade="dashboard",
        entidade_id=d.id,
        cliente_id=d.cliente_id,
        dados={"campos": sorted(body.model_dump(exclude_unset=True))},
        request=request,
    )
    db.commit()
    db.expire_all()
    return DashboardOut.model_validate(_get(db, principal, dashboard_id))


@router.delete("/{dashboard_id}", status_code=204)
def excluir(
    dashboard_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> Response:
    d = _get(db, principal, dashboard_id)
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="excluir",
        entidade="dashboard",
        entidade_id=d.id,
        cliente_id=d.cliente_id,
        dados={"nome": d.nome},
        request=request,
    )
    db.delete(d)
    db.commit()
    return Response(status_code=204)


def _widget(w: WidgetIn, ordem: int | None = None) -> Widget:
    return Widget(
        tipo=w.tipo,
        titulo=w.titulo,
        config=w.config,
        posicao=w.posicao,
        ordem=w.ordem if ordem is None else ordem,
    )


@router.post("/{dashboard_id}/widgets", response_model=WidgetOut, status_code=201)
def adicionar_widget(
    dashboard_id: uuid.UUID,
    body: WidgetIn,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> WidgetOut:
    d = _get(db, principal, dashboard_id)
    w = _widget(body)
    if not body.ordem:
        w.ordem = len(d.widgets)
    d.widgets.append(w)
    db.flush()
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="adicionar_widget",
        entidade="dashboard",
        entidade_id=d.id,
        cliente_id=d.cliente_id,
        dados={"widget_id": str(w.id), "tipo": w.tipo},
        request=request,
    )
    db.commit()
    return WidgetOut.model_validate(w)
