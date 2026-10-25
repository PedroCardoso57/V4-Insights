from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.audit import registrar
from app.core.deps import GERENCIA, Principal, get_principal, require_roles
from app.core.oidc import normalize_email
from app.core.rbac import exigir, get_cliente_autorizado, in_carteira
from app.core.sessions import now
from app.db import get_db
from app.models import Papel, Sessao, Usuario, UsuarioCliente
from app.schemas import Page, UsuarioCreate, UsuarioOut, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


def _out(u: Usuario) -> UsuarioOut:
    out = UsuarioOut.model_validate(u)
    out.vinculado_google = u.google_sub is not None
    return out


@router.get("", response_model=Page[UsuarioOut])
def listar(
    search: str | None = Query(default=None, max_length=100),
    ativo: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(require_roles(*GERENCIA)),
    db: Session = Depends(get_db),
) -> Page[UsuarioOut]:
    stmt = select(Usuario)
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(Usuario.nome).like(like), Usuario.email.like(like)))
    if ativo is not None:
        stmt = stmt.where(Usuario.ativo.is_(ativo))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Usuario.nome, Usuario.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page(items=[_out(u) for u in rows], total=total, page=page, page_size=page_size)


@router.post("", response_model=UsuarioOut, status_code=201)
def criar(
    body: UsuarioCreate,
    request: Request,
    principal: Principal = Depends(require_roles(Papel.admin)),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    email = normalize_email(body.email)
    if db.scalar(select(Usuario.id).where(Usuario.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")
    u = Usuario(nome=body.nome, email=email, papel=body.papel.value, ativo=body.ativo)
    db.add(u)
    db.flush()
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="criar",
        entidade="usuario",
        entidade_id=u.id,
        dados={"email": email, "papel": u.papel},
        request=request,
    )
    db.commit()
    return _out(u)


def _get_usuario(db: Session, usuario_id: uuid.UUID) -> Usuario:
    u = db.get(Usuario, usuario_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
    return u


@router.get("/{usuario_id}", response_model=UsuarioOut)
def obter(
    usuario_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    exigir(principal.papel in GERENCIA or principal.usuario.id == usuario_id)
    return _out(_get_usuario(db, usuario_id))


@router.patch("/{usuario_id}", response_model=UsuarioOut)
def atualizar(
    usuario_id: uuid.UUID,
    body: UsuarioUpdate,
    request: Request,
    principal: Principal = Depends(require_roles(Papel.admin)),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    u = _get_usuario(db, usuario_id)
    mudancas = body.model_dump(exclude_unset=True)
    if u.id == principal.usuario.id and (
        mudancas.get("ativo") is False or ("papel" in mudancas and mudancas["papel"] != Papel.admin)
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Não é possível remover o próprio acesso de administrador"
        )
    if body.nome is not None:
        u.nome = body.nome.strip()
    if body.papel is not None:
        u.papel = body.papel.value
    if body.ativo is not None:
        u.ativo = body.ativo
    if body.desvincular_google:
        u.google_sub = None
    if body.ativo is False or body.desvincular_google or body.papel is not None:
        # Mudanças de acesso invalidam sessões abertas.
        db.execute(
            update(Sessao)
            .where(Sessao.usuario_id == u.id, Sessao.revogada_em.is_(None))
            .values(revogada_em=now())
        )
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="editar",
        entidade="usuario",
        entidade_id=u.id,
        dados={k: str(v) for k, v in mudancas.items()},
        request=request,
    )
    db.commit()
    return _out(u)


def _checar_atribuicao(db: Session, principal: Principal, cliente_id: uuid.UUID) -> None:
    get_cliente_autorizado(db, principal, cliente_id)  # 404 se fora do escopo
    exigir(
        principal.is_admin or in_carteira(db, principal, cliente_id),
        "Somente admin atribui clientes fora da própria carteira",
    )


@router.put("/{usuario_id}/clientes/{cliente_id}", status_code=204)
def atribuir_cliente(
    usuario_id: uuid.UUID,
    cliente_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*GERENCIA)),
    db: Session = Depends(get_db),
) -> Response:
    _checar_atribuicao(db, principal, cliente_id)
    u = _get_usuario(db, usuario_id)
    if db.get(UsuarioCliente, (u.id, cliente_id)) is None:
        db.add(UsuarioCliente(usuario_id=u.id, cliente_id=cliente_id))
        registrar(
            db,
            usuario_id=principal.usuario.id,
            acao="atribuir_acesso",
            entidade="usuario_cliente",
            entidade_id=u.id,
            cliente_id=cliente_id,
            dados={"usuario_id": str(u.id)},
            request=request,
        )
        db.commit()
    return Response(status_code=204)


@router.delete("/{usuario_id}/clientes/{cliente_id}", status_code=204)
def remover_cliente(
    usuario_id: uuid.UUID,
    cliente_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*GERENCIA)),
    db: Session = Depends(get_db),
) -> Response:
    _checar_atribuicao(db, principal, cliente_id)
    vinculo = db.get(UsuarioCliente, (usuario_id, cliente_id))
    if vinculo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vínculo não encontrado")
    db.delete(vinculo)
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="remover_acesso",
        entidade="usuario_cliente",
        entidade_id=usuario_id,
        cliente_id=cliente_id,
        dados={"usuario_id": str(usuario_id)},
        request=request,
    )
    db.commit()
    return Response(status_code=204)
