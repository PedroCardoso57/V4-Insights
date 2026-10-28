from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import (
    Nivel,
    Papel,
    Plataforma,
    StatusCliente,
    StatusExecucao,
    StatusIntegracao,
    StatusJob,
    TipoJob,
)


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    """Contrato comum de listas (SPEC-08); page_size máximo: 100."""

    items: list[T]
    page: int
    page_size: int
    total: int

    @classmethod
    def unica(cls, items: list[T]) -> Page[T]:
        """Lista não paginada (poucos itens), no mesmo envelope."""
        return cls(items=items, page=1, page_size=max(len(items), 1), total=len(items))


# --- Auth / usuários -------------------------------------------------------


class MeOut(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    papel: Papel
    tem_senha: bool = False


class LoginSenhaIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)
    # False: cookie de sessão do navegador (expira ao fechar); a sessão no servidor
    # continua limitada a SESSION_TTL_HOURS em ambos os casos.
    manter_conectado: bool = True


class TrocarSenhaIn(BaseModel):
    senha_atual: str | None = Field(default=None, max_length=128)
    nova_senha: str = Field(min_length=1, max_length=128)


class DefinirSenhaIn(BaseModel):
    nova_senha: str = Field(min_length=1, max_length=128)


class UsuarioOut(ORM):
    id: uuid.UUID
    nome: str
    email: str
    papel: str
    ativo: bool
    vinculado_google: bool = False
    tem_senha: bool = False
    ultimo_login_em: datetime | None
    criado_em: datetime


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=180)
    email: EmailStr
    papel: Papel
    ativo: bool = True

    @field_validator("nome")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class UsuarioUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=180)
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
    nome: str = Field(min_length=2, max_length=180)
    nome_fantasia: str | None = Field(default=None, max_length=180)
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
    nome: str | None = Field(default=None, min_length=2, max_length=180)
    nome_fantasia: str | None = Field(default=None, max_length=180)
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


class TarefaAceita(BaseModel):
    """Resposta 202 de operações assíncronas (SPEC-08)."""

    job_id: uuid.UUID
    job_ids: list[uuid.UUID]
    status: str
    status_url: str


# --- Integrações -----------------------------------------------------------


class AutorizarIn(BaseModel):
    cliente_id: uuid.UUID
    # Reconexão de integração existente (mantém contas e histórico).
    integracao_id: uuid.UUID | None = None


class AutorizarOut(BaseModel):
    authorization_url: str


class ContaOut(ORM):
    id: uuid.UUID
    conta_externa_id: str
    nome: str
    moeda: str
    fuso_horario: str
    ativa: bool
    carga_historica_dias: int
    mapeamento_conversoes: dict[str, Any]
    ultima_sincronizacao_em: datetime | None
    dados_ate: date | None


class IntegracaoOut(ORM):
    id: uuid.UUID
    cliente_id: uuid.UUID
    plataforma: Plataforma
    status: StatusIntegracao
    escopos: list[str]
    erro_sincronizacao: str | None
    ultima_sincronizacao_em: datetime | None
    criado_em: datetime
    atualizado_em: datetime
    revogada_em: datetime | None
    contas: list[ContaOut] = []


class ContaDisponivel(BaseModel):
    conta_externa_id: str
    nome: str
    moeda: str | None = None
    fuso_horario: str | None = None
    selecionada: bool = False


class MapeamentoConversoes(BaseModel):
    """Ações do provedor contadas como conversão e janela de atribuição (opcional)."""

    action_types: list[str] = Field(default_factory=list, max_length=50)
    janela: str | None = Field(default=None, max_length=40)


class ContaSelecao(BaseModel):
    conta_externa_id: str = Field(min_length=1, max_length=255)
    carga_historica_dias: int | None = Field(default=None, ge=1, le=1095)
    mapeamento_conversoes: MapeamentoConversoes | None = None


class SelecionarContasIn(BaseModel):
    contas: list[ContaSelecao] = Field(min_length=1, max_length=100)


class SincronizarIn(BaseModel):
    conta_anuncio_id: uuid.UUID | None = None
    periodo_inicio: date | None = None
    periodo_fim: date | None = None


class SyncJobOut(ORM):
    id: uuid.UUID
    integracao_id: uuid.UUID
    conta_anuncio_id: uuid.UUID | None
    tipo: TipoJob
    status: StatusJob
    periodo_inicio: date
    periodo_fim: date
    total_registros: int
    tentativa: int
    erro_sanitizado: str | None
    iniciado_em: datetime | None
    finalizado_em: datetime | None
    proxima_tentativa_em: datetime | None
    criado_em: datetime


# --- Métricas / dashboards -------------------------------------------------


class Kpis(BaseModel):
    """Valores monetários e razões são decimais serializados como string."""

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


class Periodo(BaseModel):
    inicio: date
    fim: date


class ResumoOut(BaseModel):
    periodo: Periodo
    periodo_anterior: Periodo | None
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
    plataforma: Plataforma
    conta_anuncio_id: uuid.UUID
    campanha_externa_id: str
    campanha_nome: str | None
    kpis: Kpis


WidgetTipo = Literal["kpi", "serie", "tabela_campanhas"]


class WidgetIn(BaseModel):
    tipo: WidgetTipo
    titulo: str = Field(min_length=1, max_length=180)
    config: dict[str, Any] = Field(default_factory=dict)
    layout: dict[str, Any] = Field(default_factory=dict)
    posicao: int | None = Field(default=None, ge=0)


class WidgetOut(BaseModel):
    id: uuid.UUID
    tipo: str
    titulo: str
    config: dict[str, Any]
    layout: dict[str, Any]
    posicao: int


class DashboardIn(BaseModel):
    cliente_id: uuid.UUID
    nome: str = Field(min_length=1, max_length=180)
    descricao: str | None = Field(default=None, max_length=500)
    filtros: dict[str, Any] = Field(default_factory=dict)
    layout: dict[str, Any] = Field(default_factory=dict)


class DashboardUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=180)
    descricao: str | None = Field(default=None, max_length=500)
    filtros: dict[str, Any] | None = None
    layout: dict[str, Any] | None = None
    widgets: list[WidgetIn] | None = Field(default=None, max_length=50)


class DashboardOut(BaseModel):
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
    entidade_id: uuid.UUID | None
    cliente_id: uuid.UUID | None
    metadados: dict[str, Any]
    data_hora: datetime
    request_id: str | None


# --- Relatórios (SPEC-05) --------------------------------------------------

TemplateRelatorio = Literal["visao_executiva", "performance_campanhas"]
KpiNome = Literal[
    "investimento",
    "impressoes",
    "cliques",
    "ctr",
    "cpc",
    "cpm",
    "conversoes",
    "valor_conversoes",
    "cpa",
    "roas",
]
GraficoNome = Literal["serie_investimento", "serie_cliques", "serie_conversoes", "tabela_campanhas"]


def _kpis_padrao() -> list[KpiNome]:
    return ["investimento", "impressoes", "cliques", "ctr", "cpc", "conversoes", "cpa", "roas"]


def _graficos_padrao() -> list[GraficoNome]:
    return ["serie_investimento", "tabela_campanhas"]


class PeriodoRelatorio(BaseModel):
    tipo: Literal[
        "personalizado", "ultimos_7_dias", "ultimos_30_dias", "mes_anterior", "mes_atual"
    ] = "ultimos_30_dias"
    inicio: date | None = None
    fim: date | None = None

    @model_validator(mode="after")
    def _check(self) -> PeriodoRelatorio:
        if self.tipo == "personalizado":
            if not (self.inicio and self.fim):
                raise ValueError("período personalizado exige inicio e fim")
            if self.inicio > self.fim:
                raise ValueError("inicio deve ser <= fim")
            if (self.fim - self.inicio).days > 731:
                raise ValueError("período máximo: 2 anos")
        return self


class ConfiguracaoRelatorio(BaseModel):
    template: TemplateRelatorio = "visao_executiva"
    periodo: PeriodoRelatorio = Field(default_factory=PeriodoRelatorio)
    plataformas: list[Plataforma] = Field(default_factory=list)  # vazio = todas as fontes
    conta_anuncio_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    kpis: list[KpiNome] = Field(default_factory=_kpis_padrao, min_length=1)
    graficos: list[GraficoNome] = Field(default_factory=_graficos_padrao)
    granularidade: Literal["dia", "semana", "mes"] = "dia"
    comparar: bool = True
    comentarios: str | None = Field(default=None, max_length=5000)


class RelatorioIn(BaseModel):
    cliente_id: uuid.UUID
    titulo: str = Field(min_length=2, max_length=180)
    configuracao: ConfiguracaoRelatorio = Field(default_factory=ConfiguracaoRelatorio)


class RelatorioUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=2, max_length=180)
    configuracao: ConfiguracaoRelatorio | None = None


class RelatorioOut(ORM):
    id: uuid.UUID
    cliente_id: uuid.UUID
    criado_por: uuid.UUID
    titulo: str
    configuracao: ConfiguracaoRelatorio
    criado_em: datetime
    atualizado_em: datetime


class ExecucaoOut(ORM):
    id: uuid.UUID
    relatorio_id: uuid.UUID
    status: StatusExecucao
    progresso: int
    erro: str | None
    snapshot: dict[str, Any]
    tamanho_bytes: int | None
    iniciado_em: datetime
    finalizado_em: datetime | None
    expira_em: datetime | None
    download_url: str | None = None


class PreviewOut(BaseModel):
    """Dados que o PDF conterá, calculados agora (mesma consulta do dashboard)."""

    titulo: str
    cliente: str
    template: TemplateRelatorio
    periodo: Periodo
    periodo_anterior: Periodo | None
    resumo: ResumoOut
    serie: SerieOut | None
    campanhas: list[CampanhaOut]
    kpis: list[str]
    graficos: list[str]
    comentarios: str | None
    ultima_coleta_em: datetime | None
    gerado_em: datetime


# --- Chaves dos apps das plataformas (Configurações) ------------------------


class CampoChaveOut(BaseModel):
    chave: str
    rotulo: str
    secreto: bool
    obrigatorio: bool
    # Origem do valor em uso: "sistema" (cadastrado na tela), "env" (.env) ou None.
    origem: Literal["sistema", "env"] | None
    # Só para campos não secretos; segredos nunca saem da API.
    valor: str | None = None


class GrupoChavesOut(BaseModel):
    id: str
    nome: str
    redirect_uri: str
    configurado: bool
    campos: list[CampoChaveOut]


class ChavesIn(BaseModel):
    """Chaves a alterar. Texto grava; vazio ou null remove (volta a valer o `.env`)."""

    valores: dict[str, str | None] = Field(min_length=1, max_length=20)

    @field_validator("valores")
    @classmethod
    def _tamanho(cls, v: dict[str, str | None]) -> dict[str, str | None]:
        for valor in v.values():
            if valor is not None and len(valor) > 500:
                raise ValueError("valor muito longo (máximo 500 caracteres)")
        return v
