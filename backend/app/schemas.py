from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Nivel, Papel, Plataforma, StatusCliente


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


# --- Auth / usuários -------------------------------------------------------


class MeOut(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    papel: str
    csrf_token: str


class UsuarioOut(ORM):
    id: uuid.UUID
    nome: str
    email: str
    papel: str
    ativo: bool
    vinculado_google: bool = False
    ultimo_login_em: datetime | None
    criado_em: datetime


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    email: EmailStr
    papel: Papel
    ativo: bool = True

    @field_validator("nome")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class UsuarioUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=160)
    papel: Papel | None = None
    ativo: bool | None = None
    # Desfaz o vínculo com a conta Google (ex.: troca legítima de conta).
    desvincular_google: bool | None = None


# --- Clientes --------------------------------------------------------------

_DOC_RE = re.compile(r"\D")


def normalizar_documento(v: str | None) -> str | None:
    if v is None:
        return None
    digits = _DOC_RE.sub("", v)
    if not digits:
        return None
    if len(digits) not in (11, 14):
        raise ValueError("documento deve ser CPF (11 dígitos) ou CNPJ (14 dígitos)")
    return digits


def _strip_opt(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _nome_obrigatorio(v: str | None) -> str | None:
    v = _strip_opt(v)
    if v is not None and len(v) < 2:
        raise ValueError("nome deve ter ao menos 2 caracteres")
    return v


class ClienteBase(BaseModel):
    nome: str = Field(min_length=2, max_length=160)
    nome_fantasia: str | None = Field(default=None, max_length=160)
    documento: str | None = Field(default=None, max_length=20)

    @field_validator("nome")
    @classmethod
    def _nome(cls, v: str) -> str:
        out = _nome_obrigatorio(v)
        if out is None:
            raise ValueError("nome é obrigatório")
        return out

    @field_validator("nome_fantasia")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return _strip_opt(v)

    @field_validator("documento")
    @classmethod
    def _doc(cls, v: str | None) -> str | None:
        return normalizar_documento(v)


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=160)
    nome_fantasia: str | None = Field(default=None, max_length=160)
    documento: str | None = Field(default=None, max_length=20)

    @field_validator("nome")
    @classmethod
    def _nome(cls, v: str | None) -> str | None:
        out = _nome_obrigatorio(v)
        if v is not None and out is None:
            raise ValueError("nome é obrigatório")
        return out

    @field_validator("nome_fantasia")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return _strip_opt(v)

    @field_validator("documento")
    @classmethod
    def _doc(cls, v: str | None) -> str | None:
        return normalizar_documento(v)


class ClienteOut(ORM):
    id: uuid.UUID
    nome: str
    nome_fantasia: str | None
    documento: str | None
    status: StatusCliente
    criado_em: datetime
    atualizado_em: datetime
    arquivado_em: datetime | None


class MembroOut(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    papel: str
    ativo: bool
    atribuido_em: datetime


# --- Integrações -----------------------------------------------------------


class AutorizarIn(BaseModel):
    cliente_id: uuid.UUID
    # Reconexão de integração existente (mantém contas e histórico).
    integracao_id: uuid.UUID | None = None


class AutorizarOut(BaseModel):
    authorization_url: str


class ContaOut(ORM):
    id: uuid.UUID
    id_externo: str
    nome: str
    moeda: str | None
    fuso: str | None
    ativa: bool
    carga_historica_dias: int
    mapeamento_conversoes: dict[str, Any]
    ultima_sincronizacao_em: datetime | None
    dados_ate: date | None


class IntegracaoOut(ORM):
    id: uuid.UUID
    cliente_id: uuid.UUID
    plataforma: Plataforma
    status: str
    escopos: list[str]
    ultimo_erro: str | None
    criado_em: datetime
    atualizado_em: datetime
    revogada_em: datetime | None
    contas: list[ContaOut] = []


class ContaDisponivel(BaseModel):
    id_externo: str
    nome: str
    moeda: str | None = None
    fuso: str | None = None
    selecionada: bool = False


class ContaSelecao(BaseModel):
    id_externo: str = Field(min_length=1, max_length=64)
    carga_historica_dias: int | None = Field(default=None, ge=1, le=1095)
    mapeamento_conversoes: dict[str, Any] | None = None


class SelecionarContasIn(BaseModel):
    contas: list[ContaSelecao] = Field(min_length=1, max_length=200)


class SincronizarIn(BaseModel):
    conta_anuncio_id: uuid.UUID | None = None
    data_inicio: date | None = None
    data_fim: date | None = None


class IntegracaoAcaoIn(BaseModel):
    acao: Literal["pausar", "retomar"]


class SyncJobOut(ORM):
    id: uuid.UUID
    conta_anuncio_id: uuid.UUID
    tipo: str
    status: str
    data_inicio: date
    data_fim: date
    linhas: int
    tentativas: int
    erro: str | None
    iniciado_em: datetime | None
    finalizado_em: datetime | None
    proxima_tentativa_em: datetime | None
    criado_em: datetime


# --- Métricas / dashboards -------------------------------------------------


class Kpis(BaseModel):
    investimento: Decimal | None
    impressoes: int | None
    cliques: int | None
    conversoes: Decimal | None
    valor_conversoes: Decimal | None
    ctr: Decimal | None
    cpc: Decimal | None
    cpm: Decimal | None
    cpa: Decimal | None
    roas: Decimal | None


class ResumoOut(BaseModel):
    periodo: dict[str, date]
    periodo_anterior: dict[str, date] | None
    atual: Kpis
    anterior: Kpis | None
    variacao_percentual: dict[str, Decimal | None]
    moedas: list[str]
    ultima_sincronizacao_em: datetime | None
    integracoes_conectadas: int
    nivel: Nivel


class PontoSerie(BaseModel):
    periodo: date
    kpis: Kpis


class SerieOut(BaseModel):
    granularidade: Literal["dia", "semana", "mes"]
    pontos: list[PontoSerie]
    comparacao: list[PontoSerie] | None


class CampanhaOut(BaseModel):
    plataforma: str
    conta_anuncio_id: uuid.UUID
    campanha_externa_id: str
    campanha_nome: str | None
    kpis: Kpis


class WidgetIn(BaseModel):
    tipo: Literal["kpi", "serie", "tabela_campanhas"]
    titulo: str = Field(min_length=1, max_length=160)
    config: dict[str, Any] = Field(default_factory=dict)
    posicao: dict[str, Any] = Field(default_factory=dict)
    ordem: int = 0


class WidgetOut(ORM):
    id: uuid.UUID
    tipo: str
    titulo: str
    config: dict[str, Any]
    posicao: dict[str, Any]
    ordem: int


class DashboardIn(BaseModel):
    cliente_id: uuid.UUID
    nome: str = Field(min_length=1, max_length=160)
    descricao: str | None = Field(default=None, max_length=500)
    filtros: dict[str, Any] = Field(default_factory=dict)
    layout: dict[str, Any] = Field(default_factory=dict)


class DashboardUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=160)
    descricao: str | None = Field(default=None, max_length=500)
    filtros: dict[str, Any] | None = None
    layout: dict[str, Any] | None = None
    widgets: list[WidgetIn] | None = None


class DashboardOut(ORM):
    id: uuid.UUID
    cliente_id: uuid.UUID
    nome: str
    descricao: str | None
    filtros: dict[str, Any]
    layout: dict[str, Any]
    criado_em: datetime
    atualizado_em: datetime
    widgets: list[WidgetOut] = []


class AuditoriaOut(ORM):
    id: int
    usuario_id: uuid.UUID | None
    acao: str
    entidade: str
    entidade_id: str | None
    cliente_id: uuid.UUID | None
    dados: dict[str, Any]
    criado_em: datetime
