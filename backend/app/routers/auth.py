from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import oidc
from app.core.audit import registrar
from app.core.crypto import random_token, sha256_hex
from app.core.deps import Principal, get_principal
from app.core.sessions import clear_session_cookies, create_session, now, set_session_cookies
from app.db import get_db
from app.models import OAuthState, Usuario
from app.schemas import MeOut

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)

STATE_TTL = timedelta(minutes=10)


@router.get("/google/login")
def google_login(db: Session = Depends(get_db)) -> RedirectResponse:
    state, nonce, verifier = random_token(32), random_token(32), random_token(48)
    db.add(
        OAuthState(
            id=sha256_hex(state),
            finalidade="login",
            nonce=nonce,
            code_verifier=verifier,
            expira_em=now() + STATE_TTL,
        )
    )
    db.commit()
    return RedirectResponse(oidc.build_authorize_url(state, nonce, verifier), status_code=302)


def _consume_state(db: Session, state: str | None, finalidade: str) -> OAuthState:
    if not state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "state ausente")
    row = db.get(OAuthState, sha256_hex(state), with_for_update=True)
    if (
        row is None
        or row.finalidade != finalidade
        or row.usado_em is not None
        or row.expira_em <= now()
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "state inválido ou expirado")
    row.usado_em = now()
    db.flush()
    return row


@router.get("/google/callback")
def google_callback(
    request: Request,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    settings = get_settings()
    st = _consume_state(db, state, "login")
    db.commit()  # state é de uso único mesmo quando o login falha
    if error or not code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "autorização não concedida")
    try:
        tokens = oidc.exchange_code(code, st.code_verifier or "")
        ident = oidc.verify_id_token(tokens["id_token"], st.nonce or "")
    except oidc.OIDCError as exc:
        log.warning("login recusado: %s", exc)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de identidade inválido") from exc

    usuario = db.scalar(select(Usuario).where(Usuario.google_sub == ident.sub))
    if usuario is None:
        # Primeiro login: vincula pelo e-mail somente se ainda não houver `sub` salvo.
        usuario = db.scalar(select(Usuario).where(Usuario.email == ident.email))
        if usuario is not None and usuario.google_sub is not None:
            registrar(
                db,
                usuario_id=usuario.id,
                acao="login_negado",
                entidade="usuario",
                entidade_id=usuario.id,
                dados={"motivo": "sub_divergente"},
                request=request,
            )
            db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Conta não autorizada")
    if usuario is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Conta não autorizada")
    if not usuario.ativo:
        registrar(
            db,
            usuario_id=usuario.id,
            acao="login_negado",
            entidade="usuario",
            entidade_id=usuario.id,
            dados={"motivo": "inativo"},
            request=request,
        )
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Conta não autorizada")

    if usuario.google_sub is None:
        usuario.google_sub = ident.sub
    usuario.ultimo_login_em = now()
    token, sessao = create_session(db, usuario.id, request)
    registrar(
        db,
        usuario_id=usuario.id,
        acao="login",
        entidade="usuario",
        entidade_id=usuario.id,
        request=request,
    )
    db.commit()

    response = RedirectResponse(settings.frontend_url, status_code=302)
    set_session_cookies(response, token, sessao)
    return response


@router.get("/me", response_model=MeOut)
def me(principal: Principal = Depends(get_principal)) -> MeOut:
    u = principal.usuario
    return MeOut(
        id=u.id, nome=u.nome, email=u.email, papel=u.papel, csrf_token=principal.sessao.csrf_token
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Response:
    sessao = db.merge(principal.sessao)
    sessao.revogada_em = now()
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="logout",
        entidade="usuario",
        entidade_id=principal.usuario.id,
        request=request,
    )
    db.commit()
    response = Response(status_code=204)
    clear_session_cookies(response)
    return response
