from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import EDICAO, Principal, get_principal, require_roles
from app.api.errors import AppError
from app.api.rbac import get_cliente_autorizado, scope_clientes
from app.core.sessions import now
from app.db.session import get_db
from app.models import Relatorio, RelatorioExecucao, StatusCliente, StatusExecucao
from app.schemas import (
    ExecucaoOut,
    Page,
    RelatorioIn,
    RelatorioOut,
    RelatorioUpdate,
    TarefaAceita,
)
from app.services import relatorios as svc
from app.services import storage
from app.services.audit import registrar

router = APIRouter(prefix="/relatorios", tags=["relatorios"])
API_V1 = "/api/v1"
_KEY = re.compile(r"^[A-Za-z0-9._:-]{8,200}$")


def _get(db: Session, principal: Principal, relatorio_id: uuid.UUID) -> Relatorio:
    r = db.get(Relatorio, relatorio_id)
    if r is None or r.arquivado_em is not None:
        raise AppError(404, "Relatório não encontrado")
    get_cliente_autorizado(db, principal, r.cliente_id)  # 404 fora da carteira
    return r


def _exec_out(ex: RelatorioExecucao) -> ExecucaoOut:
    out = ExecucaoOut.model_validate(ex)
    # snapshot completo é interno; a API expõe só os metadados de captura.
    out.snapshot = {
        k: ex.snapshot.get(k) for k in ("periodo", "filtros", "horario_corte", "ultima_coleta_em")
    }
    if ex.status == StatusExecucao.concluido.value and ex.arquivo_referencia:
        out.download_url = f"{API_V1}/relatorios/execucoes/{ex.id}/download"
    return out


@router.get("", response_model=Page[RelatorioOut])
def listar(
    cliente_id: uuid.UUID | None = None,
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Page[RelatorioOut]:
    stmt = scope_clientes(select(Relatorio), principal, Relatorio.cliente_id).where(
        Relatorio.arquivado_em.is_(None)
    )
    if cliente_id:
        stmt = stmt.where(Relatorio.cliente_id == cliente_id)
    if search and search.strip():
        stmt = stmt.where(func.lower(Relatorio.titulo).like(f"%{search.strip().lower()}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Relatorio.atualizado_em.desc(), Relatorio.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[RelatorioOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=RelatorioOut, status_code=201)
def criar(
    body: RelatorioIn,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> RelatorioOut:
    cliente = get_cliente_autorizado(db, principal, body.cliente_id)
    if cliente.status == StatusCliente.arquivado.value:
        raise AppError(409, "Cliente arquivado não recebe novos relatórios")
    r = Relatorio(
        cliente_id=cliente.id,
        criado_por=principal.usuario.id,
        titulo=body.titulo,
        configuracao=body.configuracao.model_dump(mode="json"),
    )
    db.add(r)
    db.flush()
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="criar",
        entidade="relatorio",
        entidade_id=r.id,
        cliente_id=r.cliente_id,
        request=request,
    )
    db.commit()
    db.refresh(r)
    return RelatorioOut.model_validate(r)


@router.get("/execucoes/{execucao_id}/download")
def download(
    execucao_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Response:
    ex = db.get(RelatorioExecucao, execucao_id)
    if ex is None:
        raise AppError(404, "Execução não encontrada")
    r = db.get(Relatorio, ex.relatorio_id)
    assert r is not None
    # Histórico vale mesmo com cliente/relatório arquivado, mas só dentro da carteira.
    get_cliente_autorizado(db, principal, r.cliente_id)
    if ex.status != StatusExecucao.concluido.value:
        raise AppError(409, "O PDF ainda não está pronto")
    if not ex.arquivo_referencia:
        raise AppError(404, "Arquivo expirado pela política de retenção", "GONE")
    try:
        conteudo = storage.ler(ex.arquivo_referencia)
    except storage.StorageError as exc:
        raise AppError(404, "Arquivo indisponível") from exc
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="download",
        entidade="relatorio",
        entidade_id=r.id,
        cliente_id=r.cliente_id,
        dados={"execucao_id": str(ex.id)},
        request=request,
    )
    db.commit()
    nome = re.sub(r"[^A-Za-z0-9_-]+", "-", r.titulo).strip("-")[:60] or "relatorio"
    return Response(
        conteudo,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nome}-{ex.iniciado_em:%Y%m%d}.pdf"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{relatorio_id}", response_model=RelatorioOut)
def obter(
    relatorio_id: uuid.UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> RelatorioOut:
    return RelatorioOut.model_validate(_get(db, principal, relatorio_id))


@router.patch("/{relatorio_id}", response_model=RelatorioOut)
def editar(
    relatorio_id: uuid.UUID,
    body: RelatorioUpdate,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> RelatorioOut:
    r = _get(db, principal, relatorio_id)
    if body.titulo is not None:
        r.titulo = body.titulo
    if body.configuracao is not None:
        r.configuracao = body.configuracao.model_dump(mode="json")
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="editar",
        entidade="relatorio",
        entidade_id=r.id,
        cliente_id=r.cliente_id,
        dados={"campos": sorted(body.model_dump(exclude_unset=True))},
        request=request,
    )
    db.commit()
    db.refresh(r)
    return RelatorioOut.model_validate(r)


@router.delete("/{relatorio_id}", status_code=204)
def excluir(
    relatorio_id: uuid.UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> Response:
    """Exclusão lógica: o relatório sai das listas; execuções e PDFs seguem no histórico."""
    r = _get(db, principal, relatorio_id)
    r.arquivado_em = now()
    registrar(
        db,
        usuario_id=principal.usuario.id,
        acao="excluir",
        entidade="relatorio",
        entidade_id=r.id,
        cliente_id=r.cliente_id,
        dados={"titulo": r.titulo},
        request=request,
    )
    db.commit()
    return Response(status_code=204)


@router.post("/{relatorio_id}/gerar", response_model=TarefaAceita, status_code=202)
def gerar(
    relatorio_id: uuid.UUID,
    request: Request,
    idempotency_key: str | None = Header(
        default=None,
        description="Repetir a solicitação com a mesma chave devolve a mesma execução "
        "(e reprocessa o mesmo snapshot se ela tiver falhado).",
    ),
    principal: Principal = Depends(require_roles(*EDICAO)),
    db: Session = Depends(get_db),
) -> TarefaAceita:
    r = _get(db, principal, relatorio_id)
    cliente = get_cliente_autorizado(db, principal, r.cliente_id)
    if cliente.status == StatusCliente.arquivado.value:
        raise AppError(409, "Cliente arquivado: consulte o histórico de execuções")
    if idempotency_key is not None and not _KEY.match(idempotency_key):
        raise AppError(422, "Idempotency-Key inválida (8-200 caracteres alfanuméricos)")
    ex, criada = svc.solicitar(db, r, principal.usuario.id, idempotency_key)
    if criada:
        registrar(
            db,
            usuario_id=principal.usuario.id,
            acao="gerar_pdf",
            entidade="relatorio",
            entidade_id=r.id,
            cliente_id=r.cliente_id,
            dados={"execucao_id": str(ex.id)},
            request=request,
        )
    svc.agendar(db, ex, criada)
    if not criada and ex.status == StatusExecucao.erro.value:
        svc.reprocessar(db, ex)
    return TarefaAceita(
        job_id=ex.id,
        job_ids=[ex.id],
        status=ex.status,
        status_url=f"{API_V1}/relatorios/{r.id}/execucoes",
    )


@router.get("/{relatorio_id}/execucoes", response_model=Page[ExecucaoOut])
def execucoes(
    relatorio_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Page[ExecucaoOut]:
    r = db.get(Relatorio, relatorio_id)
    if r is None:
        raise AppError(404, "Relatório não encontrado")
    get_cliente_autorizado(db, principal, r.cliente_id)
    stmt = select(RelatorioExecucao).where(RelatorioExecucao.relatorio_id == r.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(RelatorioExecucao.iniciado_em.desc(), RelatorioExecucao.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(items=[_exec_out(e) for e in rows], total=total, page=page, page_size=page_size)
