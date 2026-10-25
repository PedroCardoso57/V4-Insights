"""Relatórios (SPEC-05): snapshot, geração assíncrona do PDF, retenção.

Fluxo: a solicitação congela no `snapshot` os filtros, o período resolvido, o horário de
corte, a última coleta e os números agregados (mesmas consultas do dashboard). O worker só
renderiza o snapshot — o PDF é reprodutível e bate com o dashboard daquele momento.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.sanitize import sanitize
from app.db.session import get_sessionmaker
from app.models import Cliente, Relatorio, RelatorioExecucao, StatusExecucao
from app.schemas import ConfiguracaoRelatorio, PeriodoRelatorio
from app.services import metricas, pdf, storage
from app.workers.queue import RELATORIO, enqueue

log = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


def resolver_periodo(p: PeriodoRelatorio, hoje: date) -> tuple[date, date]:
    if p.tipo == "personalizado":
        assert p.inicio and p.fim
        return p.inicio, p.fim
    if p.tipo == "ultimos_7_dias":
        return hoje - timedelta(days=6), hoje
    if p.tipo == "ultimos_30_dias":
        return hoje - timedelta(days=29), hoje
    primeiro_mes = hoje.replace(day=1)
    if p.tipo == "mes_atual":
        return primeiro_mes, hoje
    fim = primeiro_mes - timedelta(days=1)  # mes_anterior
    return fim.replace(day=1), fim


def filtros(relatorio: Relatorio, cfg: ConfiguracaoRelatorio, hoje: date) -> metricas.Filtros:
    inicio, fim = resolver_periodo(cfg.periodo, hoje)
    return metricas.Filtros(
        cliente_id=relatorio.cliente_id,
        inicio=inicio,
        fim=fim,
        plataformas=tuple(p.value for p in cfg.plataformas),
        conta_ids=tuple(cfg.conta_anuncio_ids),
    )


def capturar_snapshot(
    db: Session, relatorio: Relatorio, hoje: date | None = None
) -> dict[str, Any]:
    cfg = ConfiguracaoRelatorio.model_validate(relatorio.configuracao)
    cliente = db.get(Cliente, relatorio.cliente_id)
    f = filtros(relatorio, cfg, hoje or date.today())
    resumo = metricas.resumo(db, f, cfg.comparar)
    precisa_serie = any(g.startswith("serie_") for g in cfg.graficos)
    serie = metricas.serie(db, f, cfg.granularidade, cfg.comparar) if precisa_serie else None
    campanhas = metricas.campanhas(db, f, limit=100)
    return jsonable_encoder(
        {
            "titulo": relatorio.titulo,
            "cliente": cliente.nome if cliente else "",
            "configuracao": cfg.model_dump(mode="json"),
            "periodo": {"inicio": f.inicio, "fim": f.fim},
            "filtros": {
                "plataformas": list(f.plataformas),
                "conta_anuncio_ids": list(f.conta_ids),
                "nivel": f.nivel.value,
            },
            "horario_corte": utcnow(),
            "ultima_coleta_em": resumo.ultima_sincronizacao_em,
            "dados": {
                "resumo": resumo.model_dump(mode="json"),
                "serie": serie.model_dump(mode="json") if serie else None,
                "campanhas": [c.model_dump(mode="json") for c in campanhas],
            },
        }
    )


def solicitar(
    db: Session, relatorio: Relatorio, usuario_id: uuid.UUID, idempotency_key: str | None
) -> tuple[RelatorioExecucao, bool]:
    """Cria a execução (ou devolve a existente com a mesma chave). Retorna (execução, criada)."""
    key = idempotency_key or uuid.uuid4().hex
    snapshot = capturar_snapshot(db, relatorio)
    new_id = db.execute(
        pg_insert(RelatorioExecucao)
        .values(
            id=uuid.uuid4(),
            relatorio_id=relatorio.id,
            status=StatusExecucao.pendente.value,
            idempotency_key=key,
            solicitado_por=usuario_id,
            snapshot=snapshot,
        )
        .on_conflict_do_nothing(constraint="uq_relatorio_execucoes_idem")
        .returning(RelatorioExecucao.id)
    ).scalar()
    ex = db.scalar(
        select(RelatorioExecucao).where(
            RelatorioExecucao.relatorio_id == relatorio.id,
            RelatorioExecucao.idempotency_key == key,
        )
    )
    assert ex is not None
    return ex, new_id is not None


def agendar(db: Session, ex: RelatorioExecucao, criada: bool) -> None:
    db.commit()
    if criada:
        enqueue(RELATORIO, ex.id)


def executar(execucao_id: str | uuid.UUID) -> str:
    db = get_sessionmaker()()
    try:
        return _executar(db, uuid.UUID(str(execucao_id)))
    finally:
        db.close()


def _executar(db: Session, execucao_id: uuid.UUID) -> str:
    ex = db.scalar(
        select(RelatorioExecucao)
        .where(RelatorioExecucao.id == execucao_id)
        .with_for_update(skip_locked=True)
    )
    if ex is None or ex.status != StatusExecucao.pendente.value:
        db.rollback()
        return ex.status if ex else "inexistente"
    ex.status = StatusExecucao.processando.value
    ex.progresso = 10
    ex.erro = None
    db.commit()
    try:
        conteudo = pdf.renderizar(ex.snapshot)
        ex.progresso = 80
        ref = storage.salvar_pdf(conteudo)
    except Exception as exc:
        db.rollback()
        log.exception("falha ao gerar relatório %s", execucao_id)
        ex = db.get(RelatorioExecucao, execucao_id)
        assert ex is not None
        ex.status = StatusExecucao.erro.value
        ex.erro = sanitize(
            f"Falha ao gerar o PDF ({exc.__class__.__name__}). "
            "Gere novamente; se persistir, informe o suporte.",
            500,
        )
        ex.finalizado_em = utcnow()
        db.commit()
        return ex.status
    ex.arquivo_referencia = ref
    ex.tamanho_bytes = len(conteudo)
    ex.status = StatusExecucao.concluido.value
    ex.progresso = 100
    ex.finalizado_em = utcnow()
    ex.expira_em = utcnow() + timedelta(days=get_settings().reports_retention_days)
    db.commit()
    return ex.status


def reprocessar(db: Session, ex: RelatorioExecucao) -> bool:
    """Falha recuperável: execução em erro volta para a fila com o MESMO snapshot."""
    if ex.status != StatusExecucao.erro.value:
        return False
    ex.status = StatusExecucao.pendente.value
    ex.progresso = 0
    ex.finalizado_em = None
    db.commit()
    enqueue(RELATORIO, ex.id)
    return True


def reenfileirar_atrasados(db: Session) -> int:
    limite = utcnow() - timedelta(minutes=15)
    # "processando" há mais de 1h: worker caiu durante a geração.
    db.execute(
        update(RelatorioExecucao)
        .where(
            RelatorioExecucao.status == StatusExecucao.processando.value,
            RelatorioExecucao.iniciado_em < utcnow() - timedelta(hours=1),
        )
        .values(status=StatusExecucao.pendente.value, progresso=0)
    )
    ids = db.scalars(
        select(RelatorioExecucao.id).where(
            RelatorioExecucao.status == StatusExecucao.pendente.value,
            RelatorioExecucao.iniciado_em < limite,
        )
    ).all()
    db.commit()
    for i in ids:
        enqueue(RELATORIO, i)
    return len(ids)


def limpar_expirados(db: Session) -> int:
    """Remove PDFs vencidos do storage; o registro da execução permanece no histórico."""
    vencidas = db.scalars(
        select(RelatorioExecucao).where(
            RelatorioExecucao.expira_em < utcnow(),
            RelatorioExecucao.arquivo_referencia.is_not(None),
        )
    ).all()
    for ex in vencidas:
        try:
            storage.remover(ex.arquivo_referencia)
        except storage.StorageError:
            log.warning("referência inválida na execução %s", ex.id)
        ex.arquivo_referencia = None
    db.commit()
    return len(vencidas)
