from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.api.errors import AppError
from app.api.rbac import get_cliente_autorizado
from app.db.session import get_db
from app.models import Nivel, Plataforma
from app.schemas import CampanhaOut, Page, ResumoOut, SerieOut
from app.services import metricas as svc

router = APIRouter(prefix="/clientes/{cliente_id}", tags=["metricas"])

MAX_DIAS = 731


def filtros(
    cliente_id: uuid.UUID,
    inicio: date | None = Query(default=None, description="Início (inclusivo). Padrão: fim - 29d"),
    fim: date | None = Query(default=None, description="Fim (inclusivo). Padrão: hoje"),
    plataforma: Plataforma | None = None,
    conta_anuncio_id: uuid.UUID | None = None,
    campanha_id: str | None = Query(default=None, max_length=255),
    nivel: Nivel = Query(default=Nivel.campanha, description="Nível agregado (um por consulta)"),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> svc.Filtros:
    get_cliente_autorizado(db, principal, cliente_id)  # 404 fora da carteira
    fim = fim or date.today()
    inicio = inicio or fim - timedelta(days=29)
    if inicio > fim:
        raise AppError(422, "inicio deve ser <= fim")
    if (fim - inicio).days > MAX_DIAS:
        raise AppError(422, "período máximo: 2 anos")
    return svc.Filtros(
        cliente_id=cliente_id,
        inicio=inicio,
        fim=fim,
        plataformas=(plataforma.value,) if plataforma else (),
        conta_ids=(conta_anuncio_id,) if conta_anuncio_id else (),
        campanha_id=campanha_id,
        nivel=nivel,
    )


@router.get("/metricas/resumo", response_model=ResumoOut)
def resumo(
    comparar: bool = True,
    f: svc.Filtros = Depends(filtros),
    db: Session = Depends(get_db),
) -> ResumoOut:
    return svc.resumo(db, f, comparar)


@router.get("/metricas/serie", response_model=SerieOut)
def serie(
    granularidade: svc.Granularidade = "dia",
    comparar: bool = False,
    f: svc.Filtros = Depends(filtros),
    db: Session = Depends(get_db),
) -> SerieOut:
    return svc.serie(db, f, granularidade, comparar)


@router.get("/campanhas", response_model=Page[CampanhaOut])
def campanhas(
    ordenar_por: svc.OrdemCampanha = "investimento",
    ordem: Literal["asc", "desc"] = "desc",
    page_size: int = Query(default=100, ge=1, le=100),
    f: svc.Filtros = Depends(filtros),
    db: Session = Depends(get_db),
) -> Page[CampanhaOut]:
    """Top campanhas do período (primeira página, ordenada); `total` conta todas."""
    itens = svc.campanhas(db, f, ordenar_por, ordem, page_size)
    return Page(items=itens, page=1, page_size=page_size, total=svc.total_campanhas(db, f))
