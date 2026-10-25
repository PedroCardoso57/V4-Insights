"""Consultas agregadas de métricas (SPEC-04), compartilhadas por dashboards e relatórios.

`metricas_diarias` não tem cliente nem plataforma (baseline): ambos vêm do join com
`contas_anuncio` → `integracoes`. IDs externos só são únicos dentro da conta, por isso os
agrupamentos sempre incluem `conta_anuncio_id`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any, Literal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import ContaAnuncio, Integracao, MetricaDiaria, Nivel, StatusIntegracao
from app.schemas import CampanhaOut, Periodo, PontoSerie, ResumoOut, SerieOut
from app.services.kpis import kpis_from_row, variacoes

Granularidade = Literal["dia", "semana", "mes"]
OrdemCampanha = Literal["investimento", "impressoes", "cliques", "conversoes", "campanha_nome"]


@dataclass(frozen=True)
class Filtros:
    cliente_id: uuid.UUID
    inicio: date
    fim: date
    plataformas: tuple[str, ...] = ()
    conta_ids: tuple[uuid.UUID, ...] = ()
    campanha_id: str | None = None
    nivel: Nivel = Nivel.campanha
    extras: dict[str, Any] = field(default_factory=dict, compare=False)

    def periodo_anterior(self) -> tuple[date, date]:
        dias = (self.fim - self.inicio).days + 1
        fim_ant = self.inicio - timedelta(days=1)
        return fim_ant - timedelta(days=dias - 1), fim_ant


def _base(cols: list[Any], f: Filtros, inicio: date, fim: date) -> Select[Any]:
    # Um único nível por consulta: evita somar campanha + anúncio do mesmo gasto.
    stmt = (
        select(*cols)
        .select_from(MetricaDiaria)
        .join(ContaAnuncio, ContaAnuncio.id == MetricaDiaria.conta_anuncio_id)
        .join(Integracao, Integracao.id == ContaAnuncio.integracao_id)
        .where(
            Integracao.cliente_id == f.cliente_id,
            MetricaDiaria.nivel == f.nivel.value,
            MetricaDiaria.data >= inicio,
            MetricaDiaria.data <= fim,
        )
    )
    if f.plataformas:
        stmt = stmt.where(Integracao.plataforma.in_(f.plataformas))
    if f.conta_ids:
        stmt = stmt.where(MetricaDiaria.conta_anuncio_id.in_(f.conta_ids))
    if f.campanha_id:
        stmt = stmt.where(MetricaDiaria.campanha_externa_id == f.campanha_id)
    return stmt


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


def _tem_dados(db: Session, f: Filtros, inicio: date, fim: date) -> bool:
    return db.scalar(_base([MetricaDiaria.id], f, inicio, fim).limit(1)) is not None


def contas_ativas(db: Session, f: Filtros) -> list[ContaAnuncio]:
    q = (
        select(ContaAnuncio)
        .join(Integracao)
        .where(
            Integracao.cliente_id == f.cliente_id,
            ContaAnuncio.ativa.is_(True),
            Integracao.status == StatusIntegracao.conectada.value,
        )
    )
    if f.plataformas:
        q = q.where(Integracao.plataforma.in_(f.plataformas))
    if f.conta_ids:
        q = q.where(ContaAnuncio.id.in_(f.conta_ids))
    return list(db.scalars(q).all())


def resumo(db: Session, f: Filtros, comparar: bool = True) -> ResumoOut:
    atual = kpis_from_row(db.execute(_base(_agregados(), f, f.inicio, f.fim)).one())
    anterior = None
    periodo_ant = None
    if comparar:
        ini_a, fim_a = f.periodo_anterior()
        periodo_ant = Periodo(inicio=ini_a, fim=fim_a)
        if _tem_dados(db, f, ini_a, fim_a):
            anterior = kpis_from_row(db.execute(_base(_agregados(), f, ini_a, fim_a)).one())
    contas = contas_ativas(db, f)
    syncs = [c.ultima_sincronizacao_em for c in contas if c.ultima_sincronizacao_em]
    conectadas = db.scalar(
        select(func.count())
        .select_from(Integracao)
        .where(
            Integracao.cliente_id == f.cliente_id,
            Integracao.status == StatusIntegracao.conectada.value,
        )
    )
    moedas = db.scalars(_base([ContaAnuncio.moeda], f, f.inicio, f.fim).distinct()).all()
    return ResumoOut(
        periodo=Periodo(inicio=f.inicio, fim=f.fim),
        periodo_anterior=periodo_ant,
        atual=atual,
        anterior=anterior,
        variacao_percentual=variacoes(atual, anterior),
        moedas=sorted(m.strip() for m in moedas if m),
        # A conta sincronizada há mais tempo é quem limita a freshness do conjunto.
        ultima_sincronizacao_em=min(syncs) if syncs else None,
        integracoes_conectadas=conectadas or 0,
        nivel=f.nivel,
    )


def _pontos(
    db: Session, f: Filtros, inicio: date, fim: date, granularidade: Granularidade
) -> list[PontoSerie]:
    trunc = {"dia": "day", "semana": "week", "mes": "month"}[granularidade]
    periodo = func.date_trunc(trunc, MetricaDiaria.data).cast(MetricaDiaria.data.type)
    stmt = _base([periodo.label("periodo"), *_agregados()], f, inicio, fim)
    rows = db.execute(stmt.group_by(periodo).order_by(periodo)).all()
    return [PontoSerie(periodo=r.periodo, kpis=kpis_from_row(r)) for r in rows]


def serie(
    db: Session, f: Filtros, granularidade: Granularidade = "dia", comparar: bool = False
) -> SerieOut:
    pontos = _pontos(db, f, f.inicio, f.fim, granularidade)
    comp = None
    if comparar:
        ini_a, fim_a = f.periodo_anterior()
        comp = _pontos(db, f, ini_a, fim_a, granularidade)
    return SerieOut(granularidade=granularidade, pontos=pontos, comparacao=comp)


def campanhas(
    db: Session,
    f: Filtros,
    ordenar_por: OrdemCampanha = "investimento",
    ordem: Literal["asc", "desc"] = "desc",
    limit: int = 100,
) -> list[CampanhaOut]:
    # Tabela de campanhas sempre agrega no nível campanha.
    f = replace(f, nivel=Nivel.campanha)
    nome = func.max(MetricaDiaria.campanha_nome).label("campanha_nome")
    stmt = _base(
        [
            Integracao.plataforma,
            MetricaDiaria.conta_anuncio_id,
            MetricaDiaria.entidade_externa_id.label("campanha_externa_id"),
            nome,
            *_agregados(),
        ],
        f,
        f.inicio,
        f.fim,
    ).group_by(
        Integracao.plataforma, MetricaDiaria.conta_anuncio_id, MetricaDiaria.entidade_externa_id
    )
    col: Any = (
        nome if ordenar_por == "campanha_nome" else func.sum(getattr(MetricaDiaria, ordenar_por))
    )
    col = col.desc().nulls_last() if ordem == "desc" else col.asc().nulls_last()
    rows = db.execute(
        stmt.order_by(
            col, nome, MetricaDiaria.entidade_externa_id, MetricaDiaria.conta_anuncio_id
        ).limit(limit)
    ).all()
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


def total_campanhas(db: Session, f: Filtros) -> int:
    f = replace(f, nivel=Nivel.campanha)
    sub = (
        _base(
            [MetricaDiaria.conta_anuncio_id, MetricaDiaria.entidade_externa_id], f, f.inicio, f.fim
        )
        .distinct()
        .subquery()
    )
    return db.scalar(select(func.count()).select_from(sub)) or 0
