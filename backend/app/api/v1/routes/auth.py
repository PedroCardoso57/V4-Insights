from __future__ import annotations

import logging
from datetime import timedelta
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.api.errors import AppError
from app.core import oidc, senhas
from app.core.chaves import eh_responsavel
from app.core.config import get_settings
from app.core.crypto import random_token, sha256_hex
from app.core.ratelimit import por_ip, regra, verificar
from app.core.sessions import (
    clear_session_cookies,
    create_session,
    now,
    origin_allowed,
    set_session_cookies,
)
from app.db.session import get_db
from app.models import OAuthState, Papel, Sessao, Usuario
from app.schemas import LoginSenhaIn, MeOut, TrocarSenhaIn, TutorialIn
from app.services.audit import registrar
from app.services.fotos import url_foto

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)

STATE_TTL = timedelta(minutes=10)


@router.get("/google/login", dependencies=[Depends(por_ip("login", regra("login")))])
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


@router.get("/google/callback", dependencies=[Depends(por_ip("callback", regra("login")))])
def google_callback(
    request: Request,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    settings = get_settings()
    try:
        st = _consume_state(db, state, "login")
    except HTTPException:
        return _negar(400, "state_invalido")
    db.commit()  # state é de uso único mesmo quando o login falha
    if error or not code:
        return _negar(400, "autorizacao_cancelada")
    try:
        tokens = oidc.exchange_code(code, st.code_verifier or "")
        ident = oidc.verify_id_token(tokens["id_token"], st.nonce or "")
    except oidc.OIDCError as exc:
        log.warning("login recusado: %s", exc)
        return _negar(401, "token_invalido")

    usuario = db.scalar(select(Usuario).where(Usuario.google_sub == ident.sub))
    if usuario is None:
        # Primeiro login: vincula pelo e-mail somente se ainda não houver `sub` salvo.
        usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == ident.email))
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
            return _negar(403, "acesso_negado")
    if usuario is None:
        return _negar(403, "acesso_negado")
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
        return _negar(403, "acesso_negado")

    if usuario.google_sub is None:
        usuario.google_sub = ident.sub
    usuario.ultimo_login_em = now()
    token, csrf, _ = create_session(db, usuario.id, request)
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
    set_session_cookies(response, token, csrf)
    return response


def _negar(status_code: int, codigo: str) -> HTMLResponse:
    """Recusa o login com o status correto e leva o navegador à tela de login com o motivo.

    O status HTTP (400/401/403) é preservado para clientes de API; navegadores seguem o
    meta refresh até `/login?erro=<codigo>`.
    """
    destino = f"{get_settings().frontend_url.rstrip('/')}/login?erro={codigo}"
    html = (
        "<!doctype html><meta charset='utf-8'>"
        f"<meta http-equiv='refresh' content='0;url={escape(destino)}'>"
        f"<title>Acesso não autorizado</title><a href='{escape(destino)}'>Voltar ao login</a>"
    )
    return HTMLResponse(html, status_code=status_code)


CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos."


@router.post(
    "/login",
    status_code=204,
    dependencies=[Depends(por_ip("login", regra("login")))],
    responses={401: {"description": "Credenciais inválidas"}, 429: {"description": "Limite"}},
)
def login_senha(body: LoginSenhaIn, request: Request, db: Session = Depends(get_db)) -> Response:
    """Login por e-mail e senha para usuários pré-cadastrados com senha definida.

    A resposta é a mesma para e-mail inexistente, senha errada, usuário sem senha ou
    inativo (não revela quem está cadastrado). Sem sessão ainda, a proteção contra
    login CSRF é a verificação de Origin.
    """
    if not origin_allowed(request):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Falha na verificação de Origin")
    email = oidc.normalize_email(body.email)
    verificar(f"login_senha:email:{sha256_hex(email)}", regra("login_email")())
    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == email))
    ok = senhas.verificar(usuario.senha_hash if usuario else None, body.senha)
    if usuario is None or not ok or not usuario.ativo:
        if usuario is not None:
            motivo = "inativo" if ok else ("sem_senha" if usuario.senha_hash is None else "senha")
            registrar(
                db,
                usuario_id=usuario.id,
                acao="login_negado",
                entidade="usuario",
                entidade_id=usuario.id,
                dados={"metodo": "senha", "motivo": motivo},
                request=request,
            )
            db.commit()
        raise AppError(401, CREDENCIAIS_INVALIDAS, code="INVALID_CREDENTIALS")

    if usuario.senha_hash and senhas.precisa_rehash(usuario.senha_hash):
        usuario.senha_hash = senhas.gerar_hash(body.senha)
    usuario.ultimo_login_em = now()
    token, csrf, _ = create_session(db, usuario.id, request)
    registrar(
        db,
        usuario_id=usuario.id,
        acao="login",
        entidade="usuario",
        entidade_id=usuario.id,
        dados={"metodo": "senha"},
        request=request,
    )
    db.commit()
    response = Response(status_code=204)
    set_session_cookies(response, token, csrf, persistente=body.manter_conectado)
    return response


@router.put(
    "/senha",
    status_code=204,
    dependencies=[Depends(por_ip("senha", regra("login")))],
)
def trocar_senha(
    body: TrocarSenhaIn,
    request: Request,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Response:
    """Define ou troca a própria senha. Com senha já definida, exige a senha atual.

    As demais sessões do usuário são encerradas; a sessão atual continua válida.
    """
    u = db.merge(principal.usuario)
    if u.senha_hash is not None and not senhas.verificar(u.senha_hash, body.senha_atual or ""):
        raise AppError(400, "Senha atual incorreta.", code="INVALID_CREDENTIALS")
    try:
        senhas.validar_politica(body.nova_senha, u.email)
    except senhas.SenhaFraca as exc:
        raise AppError(422, str(exc), code="WEAK_PASSWORD") from exc
    definida = u.senha_hash is None
    u.senha_hash = senhas.gerar_hash(body.nova_senha)
    u.senha_atualizada_em = now()
    db.execute(
        update(Sessao)
        .where(
            Sessao.usuario_id == u.id,
            Sessao.revogado_em.is_(None),
            Sessao.id != principal.sessao.id,
        )
        .values(revogado_em=now())
    )
    registrar(
        db,
        usuario_id=u.id,
        acao="definir_senha" if definida else "trocar_senha",
        entidade="usuario",
        entidade_id=u.id,
        request=request,
    )
    db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=MeOut)
def me(principal: Principal = Depends(get_principal)) -> MeOut:
    u = principal.usuario
    return MeOut(
        id=u.id,
        nome=u.nome,
        email=u.email,
        papel=u.papel,
        tem_senha=u.senha_hash is not None,
        responsavel_chaves=principal.papel is Papel.admin and eh_responsavel(u.email),
        foto_url=url_foto(u.id, u.foto_atualizada_em),
        tutorial_visto=u.tutorial_visto_em is not None,
    )


@router.put("/tutorial", status_code=204)
def marcar_tutorial(
    body: TutorialIn,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Response:
    """Marca o tutorial de primeiro acesso como visto (concluído ou pulado) ou o reabre."""
    u = db.merge(principal.usuario)
    if body.visto:
        u.tutorial_visto_em = u.tutorial_visto_em or now()
    else:
        u.tutorial_visto_em = None
    db.commit()
    return Response(status_code=204)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Response:
    sessao = db.merge(principal.sessao)
    sessao.revogado_em = now()
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
