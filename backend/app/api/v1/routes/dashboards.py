from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import EDICAO, Principal, get_principal, require_roles
from app.api.errors import AppError
from app.api.rbac import get_cliente_autorizado, scope_clientes
from app.db.session import get_db
from app.models import Dashboard, DashboardWidget
from app.schemas import DashboardIn, DashboardOut, DashboardUpdate, Page, WidgetIn, WidgetOut
from app.services.audit import registrar

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _widget_out(w: DashboardWidget) -> WidgetOut:
    cfg = dict(w.configuracao or {})
    return WidgetOut(
        id=w.id,
        tipo=w.tipo,
        titulo=cfg.pop("titulo", w.tipo),
        layout=cfg.pop("layout", {}),
        config=cfg,
        posicao=w.posicao,
    )


def _out(d: Dashboard) -> DashboardOut:
    cfg = d.configuracao or {}
    return DashboardOut(
        id=d.id,
        cliente_id=d.cliente_id,
        nome=d.nome,
        descricao=cfg.get("descricao"),
        filtros=cfg.get("filtros", {}),
        layout=cfg.get("layout", {}),
        criado_em=d.criado_em,
        atualizado_em=d.atualizado_em,
        widgets=[_widget_out(w) for w in d.widgets],
    )


def _widget(w: WidgetIn, posicao: int) -> DashboardWidget:
    return DashboardWidget(
        tipo=w.tipo,
        posicao=posicao,
        configuracao={**w.config, "titulo": w.titulo, "layout": w.layout},
    )


def _get(db: Session, principal: Principal, dashboard_id: uuid.UUID) -> Dashboard:
    d = db.get(Dashboard, dashboard_id, options=[selectinload(Dashboard.widgets)])
    if d is None:
        raise AppError(404, "Dashboard não encontrado")
    get_cliente_autorizado(db, principal, d.cliente_id)
    return d


@router.get("", response_model=Page[DashboardOut])
def listar(
    cliente_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Page[DashboardOut]:
    stmt = scope_clientes(select(Dashboard), principal, Dashboard.cliente_id)
    if cliente_id:
        stmt = stmt.where(Dashboard.cliente_id == cliente_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(Dashboard.widgets))
        .order_by(Dashboard.nome, Dashboard.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=[_out(d) for d in rows], total=total, page=page, page_size=page_size)


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
        configuracao={"descricao": body.descricao, "filtros": body.filtros, "layout": body.layout},
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
    return _out(_get(db, principal, d.id))


@router.get("/{dashboard_id}", response_model=DashboardOut)
def obter(
    dashboard_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> DashboardOut:
    return _out(_get(db, principal, dashboard_id))


@router.patch("/{dashboard_id}", response_model=DashboardOut)
def editar(
    dashboard_id: uuid.UUID,
    body: DashboardUpdate,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> DashboardOut:
    d = _get(db, principal, dashboard_id)
    campos = body.model_dump(exclude_unset=True, exclude={"widgets"})
    if body.nome is not None:
        d.nome = body.nome
    cfg = dict(d.configuracao or {})
    for k in ("descricao", "filtros", "layout"):
        if k in campos and (campos[k] is not None or k == "descricao"):
            cfg[k] = campos[k]
    d.configuracao = cfg
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
    return _out(_get(db, principal, dashboard_id))


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


@router.post("/{dashboard_id}/widgets", response_model=WidgetOut, status_code=201)
def adicionar_widget(
    dashboard_id: uuid.UUID,
    body: WidgetIn,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> WidgetOut:
    d = _get(db, principal, dashboard_id)
    w = _widget(body, body.posicao if body.posicao is not None else len(d.widgets))
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
    return _widget_out(w)
