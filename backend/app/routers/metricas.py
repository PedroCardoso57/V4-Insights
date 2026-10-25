from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.deps import Principal, get_principal
from app.core.rbac import get_cliente_autorizado
from app.db import get_db
from app.metrics import kpis_from_row, variacoes
from app.models import ContaAnuncio, Integracao, MetricaDiaria, Nivel, Plataforma, StatusIntegracao
from app.schemas import CampanhaOut, PontoSerie, ResumoOut, SerieOut

router = APIRouter(prefix="/clientes/{cliente_id}", tags=["metricas"])

MAX_DIAS = 731


@dataclass
class Filtros:
    cliente_id: uuid.UUID
    inicio: date
    fim: date
    plataforma: Plataforma | None
    conta_anuncio_id: uuid.UUID | None
    campanha_id: str | None
    nivel: Nivel

    def periodo_anterior(self) -> tuple[date, date]:
        dias = (self.fim - self.inicio).days + 1
        fim_ant = self.inicio - timedelta(days=1)
        return fim_ant - timedelta(days=dias - 1), fim_ant


def filtros(
    cliente_id: uuid.UUID,
    inicio: date | None = None,
    fim: date | None = None,
    plataforma: Plataforma | None = None,
    conta_anuncio_id: uuid.UUID | None = None,
    campanha_id: str | None = Query(default=None, max_length=64),
    nivel: Nivel = Nivel.campanha,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Filtros:
    get_cliente_autorizado(db, principal, cliente_id)  # 404 fora da carteira
    fim = fim or date.today()
    inicio = inicio or fim - timedelta(days=29)
    if inicio > fim:
        raise HTTPException(422, "inicio deve ser <= fim")
    if (fim - inicio).days > MAX_DIAS:
        raise HTTPException(422, "período máximo: 2 anos")
    return Filtros(cliente_id, inicio, fim, plataforma, conta_anuncio_id, campanha_id, nivel)


def _agregados() -> list[Any]:
    # Conversões somam apenas linhas com mapeamento (NULL é ignorado pelo SUM);
    # se nenhuma linha tiver conversões mapeadas, o resultado é NULL (ausente).
    return [
        func.coalesce(func.sum(MetricaDiaria.investimento), 0).label("investimento"),
        func.coalesce(func.sum(MetricaDiaria.impressoes), 0).label("impressoes"),
        func.coalesce(func.sum(MetricaDiaria.cliques), 0).label("cliques"),
        func.sum(MetricaDiaria.conversoes).label("conversoes"),
        func.sum(MetricaDiaria.valor_conversoes).label("valor_conversoes"),
    ]


def _where(stmt: Select[Any], f: Filtros, inicio: date, fim: date) -> Select[Any]:
    # Um único nível por consulta: evita somar campanha + anúncio do mesmo gasto.
    stmt = stmt.where(
        MetricaDiaria.cliente_id == f.cliente_id,
        MetricaDiaria.nivel == f.nivel.value,
        MetricaDiaria.data >= inicio,
        MetricaDiaria.data <= fim,
    )
    if f.plataforma:
        stmt = stmt.where(MetricaDiaria.plataforma == f.plataforma.value)
    if f.conta_anuncio_id:
        stmt = stmt.where(MetricaDiaria.conta_anuncio_id == f.conta_anuncio_id)
    if f.campanha_id:
        stmt = stmt.where(MetricaDiaria.campanha_externa_id == f.campanha_id)
    return stmt


def _tem_dados(db: Session, f: Filtros, inicio: date, fim: date) -> bool:
    stmt = _where(select(MetricaDiaria.id), f, inicio, fim).limit(1)
    return db.scalar(stmt) is not None


@router.get("/metricas/resumo", response_model=ResumoOut)
def resumo(
    comparar: bool = True,
    f: Filtros = Depends(filtros),
    db: Session = Depends(get_db),
) -> ResumoOut:
    atual_row = db.execute(_where(select(*_agregados()), f, f.inicio, f.fim)).one()
    atual = kpis_from_row(atual_row)
    anterior = None
    periodo_ant = None
    if comparar:
        ini_a, fim_a = f.periodo_anterior()
        periodo_ant = {"inicio": ini_a, "fim": fim_a}
        if _tem_dados(db, f, ini_a, fim_a):
            anterior = kpis_from_row(
                db.execute(_where(select(*_agregados()), f, ini_a, fim_a)).one()
            )

    contas_q = (
        select(ContaAnuncio)
        .join(Integracao)
        .where(
            ContaAnuncio.cliente_id == f.cliente_id,
            ContaAnuncio.ativa.is_(True),
            Integracao.status == StatusIntegracao.ativa.value,
        )
    )
    if f.plataforma:
        contas_q = contas_q.where(Integracao.plataforma == f.plataforma.value)
    if f.conta_anuncio_id:
        contas_q = contas_q.where(ContaAnuncio.id == f.conta_anuncio_id)
    contas = db.scalars(contas_q).all()
    syncs = [c.ultima_sincronizacao_em for c in contas if c.ultima_sincronizacao_em]
    integ_q = (
        select(func.count())
        .select_from(Integracao)
        .where(
            Integracao.cliente_id == f.cliente_id, Integracao.status == StatusIntegracao.ativa.value
        )
    )
    moedas_q = _where(select(MetricaDiaria.moeda).distinct(), f, f.inicio, f.fim)
    return ResumoOut(
        periodo={"inicio": f.inicio, "fim": f.fim},
        periodo_anterior=periodo_ant,
        atual=atual,
        anterior=anterior,
        variacao_percentual=variacoes(atual, anterior),
        moedas=sorted(m for m in db.scalars(moedas_q) if m),
        # A informação mais antiga entre as contas é o que limita a freshness.
        ultima_sincronizacao_em=min(syncs) if syncs else None,
        integracoes_conectadas=db.scalar(integ_q) or 0,
        nivel=f.nivel,
    )


def _serie(
    db: Session, f: Filtros, inicio: date, fim: date, granularidade: str
) -> list[PontoSerie]:
    trunc = {"dia": "day", "semana": "week", "mes": "month"}[granularidade]
    periodo = func.date_trunc(trunc, MetricaDiaria.data).cast(MetricaDiaria.data.type)
    stmt = _where(select(periodo.label("periodo"), *_agregados()), f, inicio, fim)
    rows = db.execute(stmt.group_by(periodo).order_by(periodo)).all()
    return [PontoSerie(periodo=r.periodo, kpis=kpis_from_row(r)) for r in rows]


@router.get("/metricas/serie", response_model=SerieOut)
def serie(
    granularidade: Literal["dia", "semana", "mes"] = "dia",
    comparar: bool = False,
    f: Filtros = Depends(filtros),
    db: Session = Depends(get_db),
) -> SerieOut:
    pontos = _serie(db, f, f.inicio, f.fim, granularidade)
    comp = None
    if comparar:
        ini_a, fim_a = f.periodo_anterior()
        comp = _serie(db, f, ini_a, fim_a, granularidade)
    return SerieOut(granularidade=granularidade, pontos=pontos, comparacao=comp)


@router.get("/campanhas", response_model=list[CampanhaOut])
def campanhas(
    ordenar_por: Literal[
        "investimento", "impressoes", "cliques", "conversoes", "campanha_nome"
    ] = "investimento",
    ordem: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=100, ge=1, le=500),
    f: Filtros = Depends(filtros),
    db: Session = Depends(get_db),
) -> list[CampanhaOut]:
    # Tabela de campanhas sempre agrega no nível campanha.
    f = Filtros(
        f.cliente_id,
        f.inicio,
        f.fim,
        f.plataforma,
        f.conta_anuncio_id,
        f.campanha_id,
        Nivel.campanha,
    )
    nome = func.max(MetricaDiaria.campanha_nome).label("campanha_nome")
    stmt = _where(
        select(
            MetricaDiaria.plataforma,
            MetricaDiaria.conta_anuncio_id,
            MetricaDiaria.entidade_externa_id.label("campanha_externa_id"),
            nome,
            *_agregados(),
        ),
        f,
        f.inicio,
        f.fim,
    ).group_by(
        MetricaDiaria.plataforma, MetricaDiaria.conta_anuncio_id, MetricaDiaria.entidade_externa_id
    )
    col: Any = (
        nome if ordenar_por == "campanha_nome" else func.sum(getattr(MetricaDiaria, ordenar_por))
    )
    col = col.desc().nulls_last() if ordem == "desc" else col.asc().nulls_last()
    rows = db.execute(stmt.order_by(col, MetricaDiaria.entidade_externa_id).limit(limit)).all()
    return [
        CampanhaOut(
            plataforma=r.plataforma,
            conta_anuncio_id=r.conta_anuncio_id,
            campanha_externa_id=r.campanha_externa_id,
            campanha_nome=r.campanha_nome,
            kpis=kpis_from_row(r),
        )
        for r in rows
    ]
