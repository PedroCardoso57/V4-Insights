from __future__ import annotations

import contextlib
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import GERENCIA, Principal, get_principal, require_roles
from app.api.rbac import get_cliente_autorizado, scope_clientes
from app.core.sessions import now
from app.db.session import get_db
from app.models import Cliente, Papel, StatusCliente, Usuario, UsuarioCliente
from app.schemas import ClienteCreate, ClienteOut, ClienteUpdate, MembroOut, Page
from app.services import clientes as svc_clientes
from app.services import storage
from app.services.audit import registrar

router = APIRouter(prefix="/clientes", tags=["clientes"])

ORDENACAO: dict[str, Any] = {
    "nome": Cliente.nome,
    "criado_em": Cliente.criado_em,
    "atualizado_em": Cliente.atualizado_em,
}


@router.get("", response_model=Page[ClienteOut])
def listar(
    search: str | None = Query(default=None, max_length=100),
    status_: StatusCliente | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    order_by: Literal["nome", "criado_em", "atualizado_em"] = "nome",
    order: Literal["asc", "desc"] = "asc",
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Page[ClienteOut]:
    stmt = scope_clientes(select(Cliente), principal, Cliente.id)
    if search and search.strip():
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(func.lower(Cliente.nome).like(like), func.lower(Cliente.nome_fantasia).like(like))
        )
    if status_ is not None:
        stmt = stmt.where(Cliente.status == status_.value)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    col = ORDENACAO[order_by]
    # Desempate por id garante paginação estável.
    ordem: list[Any] = (
        [col.desc(), Cliente.id.desc()] if order == "desc" else [col.asc(), Cliente.id.asc()]
    )
    rows = db.scalars(stmt.order_by(*ordem).offset((page - 1) * page_size).limit(page_size)).all()
    return Page(
        items=[ClienteOut.model_validate(c) for c in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ClienteOut, status_code=201)
def criar(
    body: ClienteCreate,
    request: Request,
    principal: Principal = Depends(require_roles(*GERENCIA)),
    db: Session = Depends(get_db),
) -> ClienteOut:
    c = Cliente(
        nome=body.nome,
        nome_fantasia=body.nome_fantasia,
        documento=body.documento,
        status=StatusCliente.ativo.value,
    )
    db.add(c)
    db.flush()
    if principal.papel is Papel.gestor:
        # Gestor que cria um cliente passa a tê-lo na própria carteira.
        db.add(UsuarioCliente(usuario_id=principal.usuario.id, cliente_id=c.id))
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="criar",
        entidade="cliente",
        entidade_id=c.id,
        cliente_id=c.id,
        dados=body.model_dump(),
        request=request,
    )
    db.commit()
    db.refresh(c)
    return ClienteOut.model_validate(c)


@router.get("/{cliente_id}", response_model=ClienteOut)
def obter(
    cliente_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> ClienteOut:
    return ClienteOut.model_validate(get_cliente_autorizado(db, principal, cliente_id))


@router.patch("/{cliente_id}", response_model=ClienteOut)
def editar(
    cliente_id: uuid.UUID,
    body: ClienteUpdate,
    request: Request,
    principal: Principal = Depends(require_roles(*GERENCIA)),
    db: Session = Depends(get_db),
) -> ClienteOut:
    c = get_cliente_autorizado(db, principal, cliente_id)
    if c.status == StatusCliente.arquivado.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cliente arquivado não pode ser editado")
    mudancas = body.model_dump(exclude_unset=True)
    if "nome" in mudancas and mudancas["nome"] is None:
        raise HTTPException(422, "nome é obrigatório")
    antes = {k: getattr(c, k) for k in mudancas}
    for k, v in mudancas.items():
        setattr(c, k, v)
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="editar",
        entidade="cliente",
        entidade_id=c.id,
        cliente_id=c.id,
        dados={"antes": antes, "depois": mudancas},
        request=request,
    )
    db.commit()
    db.refresh(c)
    return ClienteOut.model_validate(c)


@router.post("/{cliente_id}/arquivar", response_model=ClienteOut)
def arquivar(
    cliente_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*GERENCIA)),
    db: Session = Depends(get_db),
) -> ClienteOut:
    c = get_cliente_autorizado(db, principal, cliente_id)
    if c.status != StatusCliente.arquivado.value:
        # Arquivamento lógico: métricas, relatórios e integrações permanecem no banco.
        c.status = StatusCliente.arquivado.value
        c.arquivado_em = now()
        registrar(
            db,
            usuario_id=principal.usuario.id,
            acao="arquivar",
            entidade="cliente",
            entidade_id=c.id,
            cliente_id=c.id,
            request=request,
        )
        db.commit()
        db.refresh(c)
    return ClienteOut.model_validate(c)


@router.delete("/{cliente_id}", status_code=204)
def excluir(
    cliente_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require_roles(Papel.admin)),
    db: Session = Depends(get_db),
) -> Response:
    """Exclui o cliente definitivamente, com integrações, métricas, dashboards e relatórios.
    Irreversível; para apenas tirar o cliente de circulação, use o arquivamento."""
    c = get_cliente_autorizado(db, principal, cliente_id)
    pdfs = svc_clientes.excluir(db, c, ator_id=principal.usuario.id, request=request)
    db.commit()
    for ref in pdfs:
        with contextlib.suppress(storage.StorageError):
            storage.remover(ref)
    return Response(status_code=204)


@router.get("/{cliente_id}/usuarios", response_model=Page[MembroOut])
def membros(
    cliente_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Page[MembroOut]:
    get_cliente_autorizado(db, principal, cliente_id)
    rows = db.execute(
        select(Usuario, UsuarioCliente.criado_em)
        .join(UsuarioCliente, UsuarioCliente.usuario_id == Usuario.id)
        .where(UsuarioCliente.cliente_id == cliente_id)
        .order_by(Usuario.nome)
    ).all()
    return Page.unica(
        [
            MembroOut(
                id=u.id,
                nome=u.nome,
                email=u.email,
                papel=u.papel,
                ativo=u.ativo,
                atribuido_em=criado,
            )
            for u, criado in rows
        ]
    )
