"""Escopo de carteira: cada usuário só enxerga clientes atribuídos (admin vê todos)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.api.deps import Principal
from app.models import Cliente, Papel, UsuarioCliente


def carteira_subquery(principal: Principal) -> Select[Any]:
    return select(UsuarioCliente.cliente_id).where(
        UsuarioCliente.usuario_id == principal.usuario.id
    )


def scope_clientes(stmt: Select[Any], principal: Principal, column: Any) -> Select[Any]:
    """Restringe `stmt` aos clientes autorizados, usando `column` como cliente_id."""
    if principal.is_admin:
        return stmt
    return stmt.where(column.in_(carteira_subquery(principal)))


def in_carteira(db: Session, principal: Principal, cliente_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(UsuarioCliente.cliente_id).where(
                UsuarioCliente.usuario_id == principal.usuario.id,
                UsuarioCliente.cliente_id == cliente_id,
            )
        )
        is not None
    )


def get_cliente_autorizado(db: Session, principal: Principal, cliente_id: uuid.UUID) -> Cliente:
    """Retorna o cliente ou 404 — nunca revela a existência de clientes alheios."""
    cliente = db.get(Cliente, cliente_id)
    if cliente is None or not (principal.is_admin or in_carteira(db, principal, cliente_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    return cliente


def pode_gerir_cliente(principal: Principal) -> bool:
    return principal.papel in (Papel.admin, Papel.gestor)


def exigir(cond: bool, msg: str = "Permissão insuficiente") -> None:
    if not cond:
        raise HTTPException(status.HTTP_403_FORBIDDEN, msg)
