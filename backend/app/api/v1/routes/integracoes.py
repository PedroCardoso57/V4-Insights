from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import EDICAO, Principal, require_roles
from app.api.errors import AppError
from app.api.rbac import get_cliente_autorizado, scope_clientes
from app.core.config import get_settings
from app.core.crypto import delete_secret, load_secret, random_token, sha256_hex, store_secret
from app.core.ratelimit import por_usuario, regra
from app.core.sanitize import sanitize
from app.core.sessions import now
from app.db.session import get_db
from app.integrations.base import (
    AdsProvider,
    ConfigProviderError,
    PermissionProviderError,
    ProviderError,
)
from app.integrations.registry import get_provider, mapeamento_padrao
from app.models import (
    ContaAnuncio,
    Integracao,
    OAuthState,
    Plataforma,
    StatusCliente,
    StatusIntegracao,
    StatusJob,
    SyncJob,
    TipoJob,
)
from app.schemas import (
    AutorizarIn,
    AutorizarOut,
    ContaDisponivel,
    IntegracaoOut,
    Page,
    SelecionarContasIn,
    SincronizarIn,
    SyncJobOut,
    TarefaAceita,
)
from app.services import sync
from app.services.audit import registrar

router = APIRouter(prefix="/integracoes", tags=["integracoes"])
API_V1 = "/api/v1"
log = logging.getLogger(__name__)
STATE_TTL = timedelta(minutes=15)


def _integracao_autorizada(
    db: Session, principal: Principal, integracao_id: uuid.UUID
) -> Integracao:
    integ = db.get(Integracao, integracao_id, options=[selectinload(Integracao.contas)])
    if integ is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integração não encontrada")
    get_cliente_autorizado(db, principal, integ.cliente_id)  # 404 se fora da carteira
    return integ


def _provider(plataforma: str) -> AdsProvider:
    try:
        return get_provider(plataforma)
    except ConfigProviderError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


def _erro_provedor(exc: ProviderError) -> AppError:
    """502 para recusa/erro do provedor; 503 para quota ou indisponibilidade temporária."""
    msg = f"Falha ao consultar o provedor: {sanitize(str(exc), 300)}"
    if exc.retryable:
        return AppError(503, msg, "PROVIDER_UNAVAILABLE")
    if isinstance(exc, PermissionProviderError):
        return AppError(502, msg, "PROVIDER_PERMISSION")
    return AppError(502, msg, "PROVIDER_ERROR")


@router.get("", response_model=Page[IntegracaoOut])
def listar(
    cliente_id: uuid.UUID | None = None,
    plataforma: Plataforma | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> Page[IntegracaoOut]:
    stmt = scope_clientes(select(Integracao), principal, Integracao.cliente_id)
    if cliente_id:
        stmt = stmt.where(Integracao.cliente_id == cliente_id)
    if plataforma:
        stmt = stmt.where(Integracao.plataforma == plataforma.value)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(Integracao.contas))
        .order_by(Integracao.criado_em.desc(), Integracao.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[IntegracaoOut.model_validate(i) for i in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{plataforma}/autorizar",
    response_model=AutorizarOut,
    dependencies=[Depends(por_usuario("autorizar", regra("caro")))],
)
def autorizar(
    plataforma: Plataforma,
    body: AutorizarIn,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> AutorizarOut:
    cliente = get_cliente_autorizado(db, principal, body.cliente_id)
    if cliente.status == StatusCliente.arquivado.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Não é possível criar integrações para cliente arquivado"
        )
    if body.integracao_id:
        integ = _integracao_autorizada(db, principal, body.integracao_id)
        if integ.cliente_id != cliente.id or integ.plataforma != plataforma.value:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Integração não corresponde")
    provider = _provider(plataforma.value)
    state, verifier = random_token(32), random_token(48)
    db.add(
        OAuthState(
            id=sha256_hex(state),
            finalidade=plataforma.value,
            code_verifier=verifier,
            usuario_id=principal.usuario.id,
            cliente_id=cliente.id,
            integracao_id=body.integracao_id,
            expira_em=now() + STATE_TTL,
        )
    )
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="iniciar_conexao",
        entidade="integracao",
        entidade_id=body.integracao_id,
        cliente_id=cliente.id,
        dados={"plataforma": plataforma.value},
        request=request,
    )
    db.commit()
    return AutorizarOut(authorization_url=provider.authorize_url(state, verifier))


@router.get("/{plataforma}/callback")
def callback(
    plataforma: Plataforma,
    request: Request,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    front = get_settings().frontend_url.rstrip("/")
    if not state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "state ausente")
    st = db.get(OAuthState, sha256_hex(state), with_for_update=True)
    # O state precisa ter sido emitido para ESTE usuário, cliente e provedor.
    if (
        st is None
        or st.finalidade != plataforma.value
        or st.usado_em is not None
        or st.expira_em <= now()
        or st.usuario_id != principal.usuario.id
        or st.cliente_id is None
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "state inválido ou expirado")
    st.usado_em = now()
    db.commit()
    cliente = get_cliente_autorizado(db, principal, st.cliente_id)
    destino = f"{front}/integracoes?cliente_id={cliente.id}"
    if error or not code:
        return RedirectResponse(f"{destino}&erro=autorizacao_negada", status_code=302)
    if cliente.status == StatusCliente.arquivado.value:
        return RedirectResponse(f"{destino}&erro=cliente_arquivado", status_code=302)

    provider = _provider(plataforma.value)
    try:
        creds = provider.exchange_code(code, st.code_verifier or "")
    except ProviderError as exc:
        log.warning("conexão %s recusada: %s", plataforma.value, exc)
        return RedirectResponse(f"{destino}&erro=conexao_recusada", status_code=302)

    integ = db.get(Integracao, st.integracao_id) if st.integracao_id else None
    if integ is None:
        integ = Integracao(
            cliente_id=cliente.id,
            plataforma=plataforma.value,
            status=StatusIntegracao.pendente.value,
        )
        db.add(integ)
        db.flush()
        acao = "conectar"
    else:
        acao = "reconectar"
    integ.referencia_credencial = store_secret(
        db, creds, integ.referencia_credencial, integracao_id=integ.id
    )
    integ.escopos = list(creds.get("scopes") or [])
    integ.conectado_por = principal.usuario.id
    integ.erro_sincronizacao = None
    integ.revogada_em = None
    tem_contas = db.scalar(
        select(ContaAnuncio.id).where(ContaAnuncio.integracao_id == integ.id).limit(1)
    )
    integ.status = (StatusIntegracao.conectada if tem_contas else StatusIntegracao.pendente).value
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao=acao,
        entidade="integracao",
        entidade_id=integ.id,
        cliente_id=cliente.id,
        dados={"plataforma": plataforma.value},
        request=request,
    )
    db.commit()
    return RedirectResponse(f"{destino}&integracao={integ.id}", status_code=302)


@router.get("/{integracao_id}/contas", response_model=Page[ContaDisponivel])
def contas_disponiveis(
    integracao_id: uuid.UUID,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> Page[ContaDisponivel]:
    integ = _integracao_autorizada(db, principal, integracao_id)
    if integ.status == StatusIntegracao.revogada.value or not integ.referencia_credencial:
        raise HTTPException(status.HTTP_409_CONFLICT, "Integração revogada; reconecte")
    provider = _provider(integ.plataforma)
    creds = load_secret(db, integ.referencia_credencial)
    try:
        if renovadas := provider.ensure_fresh(creds):
            store_secret(db, renovadas, integ.referencia_credencial)
            db.commit()
            creds = renovadas
        externas = provider.list_accounts(creds)
    except ProviderError as exc:
        raise _erro_provedor(exc) from exc
    selecionadas = {c.conta_externa_id for c in integ.contas if c.ativa}
    return Page.unica(
        [
            ContaDisponivel(
                conta_externa_id=e.id_externo,
                nome=e.nome,
                moeda=e.moeda,
                fuso_horario=e.fuso,
                selecionada=e.id_externo in selecionadas,
            )
            for e in externas
        ]
    )


@router.post("/{integracao_id}/contas", response_model=IntegracaoOut)
def selecionar_contas(
    integracao_id: uuid.UUID,
    body: SelecionarContasIn,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> IntegracaoOut:
    integ = _integracao_autorizada(db, principal, integracao_id)
    cliente = get_cliente_autorizado(db, principal, integ.cliente_id)
    if cliente.status == StatusCliente.arquivado.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cliente arquivado")
    if integ.status == StatusIntegracao.revogada.value or not integ.referencia_credencial:
        raise HTTPException(status.HTTP_409_CONFLICT, "Integração revogada; reconecte")
    provider = _provider(integ.plataforma)
    creds = load_secret(db, integ.referencia_credencial)
    try:
        if renovadas := provider.ensure_fresh(creds):
            store_secret(db, renovadas, integ.referencia_credencial)
            creds = renovadas
        disponiveis = {e.id_externo: e for e in provider.list_accounts(creds)}
    except ProviderError as exc:
        raise _erro_provedor(exc) from exc

    # Só aceita contas que o provedor confirma estarem autorizadas para este token.
    invalidas = [c.conta_externa_id for c in body.contas if c.conta_externa_id not in disponiveis]
    if invalidas:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Contas não autorizadas: {', '.join(invalidas[:10])}"
        )
    existentes = {c.conta_externa_id: c for c in integ.contas}
    pedidas = {c.conta_externa_id for c in body.contas}
    novas: list[ContaAnuncio] = []
    for sel in body.contas:
        ext = disponiveis[sel.conta_externa_id]
        conta = existentes.get(sel.conta_externa_id)
        if conta is None:
            conta = ContaAnuncio(
                integracao_id=integ.id,
                conta_externa_id=ext.id_externo,
                nome=ext.nome,
                moeda=ext.moeda or "BRL",
                fuso_horario=ext.fuso or "America/Sao_Paulo",
                carga_historica_dias=sel.carga_historica_dias
                or get_settings().sync_history_days_default,
                mapeamento_conversoes=sel.mapeamento_conversoes.model_dump(exclude_none=True)
                if sel.mapeamento_conversoes is not None
                else mapeamento_padrao(integ.plataforma),
            )
            db.add(conta)
            novas.append(conta)
        else:
            reativada = not conta.ativa
            conta.ativa = True
            conta.nome = ext.nome
            conta.moeda = ext.moeda or conta.moeda
            conta.fuso_horario = ext.fuso or conta.fuso_horario
            if sel.carga_historica_dias:
                conta.carga_historica_dias = sel.carga_historica_dias
            novo_map = (
                sel.mapeamento_conversoes.model_dump(exclude_none=True)
                if sel.mapeamento_conversoes is not None
                else None
            )
            if novo_map is not None and novo_map != conta.mapeamento_conversoes:
                conta.mapeamento_conversoes = novo_map
                db.flush()
                sync.recalcular_conversoes(db, conta)
            if reativada:
                novas.append(conta)
    for id_ext, conta in existentes.items():
        if id_ext not in pedidas:
            conta.ativa = False  # desmarcada: preserva histórico, para de coletar
    if integ.status in (StatusIntegracao.pendente.value, StatusIntegracao.erro.value):
        integ.status = StatusIntegracao.conectada.value
    db.flush()
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="selecionar_contas",
        entidade="integracao",
        entidade_id=integ.id,
        cliente_id=integ.cliente_id,
        dados={"contas": sorted(pedidas)},
        request=request,
    )
    db.commit()

    # Carga histórica para contas novas ou reativadas.
    if integ.status == StatusIntegracao.conectada.value:
        for conta in novas:
            fim = sync.hoje_conta(conta)
            inicio = fim - timedelta(days=conta.carga_historica_dias)
            job, criado = sync.criar_job(
                db, conta, TipoJob.historico, inicio, fim, principal.usuario.id
            )
            sync.agendar(db, job, criado)
    db.refresh(integ)
    return IntegracaoOut.model_validate(integ)


@router.post(
    "/{integracao_id}/sincronizar",
    response_model=TarefaAceita,
    status_code=202,
    dependencies=[Depends(por_usuario("sincronizar", regra("caro")))],
)
def sincronizar(
    integracao_id: uuid.UUID,
    request: Request,
    body: SincronizarIn | None = None,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> TarefaAceita:
    body = body or SincronizarIn()
    integ = _integracao_autorizada(db, principal, integracao_id)
    cliente = get_cliente_autorizado(db, principal, integ.cliente_id)
    if integ.status != StatusIntegracao.conectada.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Integração {integ.status}: sincronização indisponível"
        )
    if cliente.status == StatusCliente.arquivado.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cliente arquivado")
    contas = [c for c in integ.contas if c.ativa]
    if body.conta_anuncio_id:
        contas = [c for c in contas if c.id == body.conta_anuncio_id]
        if not contas:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conta não encontrada")
    if not contas:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nenhuma conta selecionada")
    if body.periodo_inicio and body.periodo_fim and body.periodo_inicio > body.periodo_fim:
        raise HTTPException(422, "Intervalo inválido")
    jobs: list[SyncJob] = []
    for conta in contas:
        padrao_inicio, padrao_fim = sync.janela_incremental(conta)
        inicio = body.periodo_inicio or padrao_inicio
        fim = body.periodo_fim or padrao_fim
        if (fim - inicio).days > 1095:
            raise HTTPException(422, "Intervalo máximo: 3 anos")
        job, criado = sync.criar_job(db, conta, TipoJob.manual, inicio, fim, principal.usuario.id)
        if criado:
            registrar(
                db,
                usuario_id=principal.usuario.id,
                acao="sincronizar",
                entidade="integracao",
                entidade_id=integ.id,
                cliente_id=integ.cliente_id,
                dados={
                    "conta": conta.conta_externa_id,
                    "inicio": inicio.isoformat(),
                    "fim": fim.isoformat(),
                },
                request=request,
            )
        sync.agendar(db, job, criado)
        jobs.append(job)
    return TarefaAceita(
        job_id=jobs[0].id,
        job_ids=[j.id for j in jobs],
        status=jobs[0].status,
        status_url=f"{API_V1}/integracoes/{integ.id}/jobs",
    )


@router.get("/{integracao_id}/jobs", response_model=Page[SyncJobOut])
def jobs(
    integracao_id: uuid.UUID,
    status_: StatusJob | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> Page[SyncJobOut]:
    _integracao_autorizada(db, principal, integracao_id)
    stmt = select(SyncJob).where(SyncJob.integracao_id == integracao_id)
    if status_:
        stmt = stmt.where(SyncJob.status == status_.value)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(SyncJob.criado_em.desc(), SyncJob.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[SyncJobOut.model_validate(j) for j in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _set_status(
    db: Session, principal: Principal, integracao_id: uuid.UUID, acao: str, request: Request
) -> Integracao:
    integ = _integracao_autorizada(db, principal, integracao_id)
    if integ.status == StatusIntegracao.revogada.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Integração revogada; reconecte")
    if acao == "pausar":
        integ.status = StatusIntegracao.pausada.value
        sync.cancelar_pendentes(db, integ.id, "integração pausada")
    else:
        if integ.status != StatusIntegracao.pausada.value:
            raise HTTPException(status.HTTP_409_CONFLICT, "Integração não está pausada")
        tem_contas = any(c.ativa for c in integ.contas)
        integ.status = (
            StatusIntegracao.conectada if tem_contas else StatusIntegracao.pendente
        ).value
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao=acao,
        entidade="integracao",
        entidade_id=integ.id,
        cliente_id=integ.cliente_id,
        request=request,
    )
    db.commit()
    db.refresh(integ)
    return integ


@router.post("/{integracao_id}/pausar", response_model=IntegracaoOut)
def pausar(
    integracao_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> IntegracaoOut:
    return IntegracaoOut.model_validate(
        _set_status(db, principal, integracao_id, "pausar", request)
    )


@router.post("/{integracao_id}/retomar", response_model=IntegracaoOut)
def retomar(
    integracao_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> IntegracaoOut:
    return IntegracaoOut.model_validate(
        _set_status(db, principal, integracao_id, "retomar", request)
    )


@router.post("/{integracao_id}/revogar", response_model=IntegracaoOut)
def revogar(
    integracao_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> IntegracaoOut:
    integ = _integracao_autorizada(db, principal, integracao_id)
    if integ.status != StatusIntegracao.revogada.value:
        if integ.referencia_credencial:
            try:
                creds = load_secret(db, integ.referencia_credencial)
                _provider(integ.plataforma).revoke(creds)
            except Exception as exc:  # revogação remota é best-effort
                log.warning("revogação remota falhou: %s", sanitize(str(exc)))
            delete_secret(db, integ.referencia_credencial)
        integ.referencia_credencial = None
        integ.status = StatusIntegracao.revogada.value
        integ.revogada_em = now()
        sync.cancelar_pendentes(db, integ.id, "integração revogada")
        registrar(
            db,
            usuario_id=principal.usuario.id,
            acao="revogar",
            entidade="integracao",
            entidade_id=integ.id,
            cliente_id=integ.cliente_id,
            request=request,
        )
        db.commit()
        db.refresh(integ)
    return IntegracaoOut.model_validate(integ)
