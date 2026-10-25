from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.sessions import SAFE_METHODS, csrf_valid, find_active_session, origin_allowed
from app.db.session import get_db
from app.models import Papel, Sessao, Usuario


@dataclass
class Principal:
    usuario: Usuario
    sessao: Sessao

    @property
    def papel(self) -> Papel:
        return Papel(self.usuario.papel)

    @property
    def is_admin(self) -> bool:
        return self.papel is Papel.admin


def get_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    token = request.cookies.get(get_settings().session_cookie_name)
    sessao = find_active_session(db, token)
    if sessao is None or not sessao.usuario.ativo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada")
    if request.method not in SAFE_METHODS and not (
        origin_allowed(request) and csrf_valid(request, sessao)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Falha na verificação CSRF/Origin")
    return Principal(usuario=sessao.usuario, sessao=sessao)


def require_roles(*papeis: Papel) -> Callable[[Principal], Principal]:
    allowed = set(papeis)

    def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.papel not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente")
        return principal

    return _dep


# Conjuntos de papéis por capacidade (SPEC-01).
GERENCIA = (Papel.admin, Papel.gestor)
EDICAO = (Papel.admin, Papel.gestor, Papel.analista)
TODOS = tuple(Papel)
