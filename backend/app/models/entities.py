"""Modelos ORM.

O schema é versionado por Alembic: `0001` reproduz a baseline `001_initial.sql` e `0002`
aplica os ajustes da SPEC-08. Estes modelos refletem o estado após `head` — `alembic check`
garante que não divergem das migrations.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Papel(enum.StrEnum):
    admin = "admin"
    gestor = "gestor"
    analista = "analista"
    visualizador = "visualizador"


class StatusCliente(enum.StrEnum):
    ativo = "ativo"
    inativo = "inativo"  # herdado da baseline
    arquivado = "arquivado"


class Plataforma(enum.StrEnum):
    meta_ads = "meta_ads"
    google_ads = "google_ads"
    linkedin_ads = "linkedin_ads"
    tiktok_ads = "tiktok_ads"


class StatusIntegracao(enum.StrEnum):
    pendente = "pendente"  # autorizada, aguardando seleção de contas
    conectada = "conectada"
    pausada = "pausada"
    erro = "erro"  # credencial inválida / permissão retirada: requer reconexão
    revogada = "revogada"


class TipoJob(enum.StrEnum):
    historico = "historico"
    incremental = "incremental"
    manual = "manual"


class StatusJob(enum.StrEnum):
    pendente = "pendente"
    executando = "executando"
    sucesso = "sucesso"
    erro = "erro"
    cancelado = "cancelado"


class Nivel(enum.StrEnum):
    conta = "conta"
    campanha = "campanha"
    conjunto = "conjunto"
    anuncio = "anuncio"


class StatusExecucao(enum.StrEnum):
    pendente = "pendente"
    processando = "processando"
    concluido = "concluido"
    erro = "erro"


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


def _ts(nullable: bool = False, **kw: Any) -> Any:
    if nullable:
        return mapped_column(DateTime(timezone=True), nullable=True, **kw)
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), **kw)


def _jsonb() -> Any:
    return mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))


# --- Baseline (001_initial.sql) + ajustes 0002 ----------------------------


class Perfil(Base):
    __tablename__ = "perfis"

    id: Mapped[uuid.UUID] = _uuid_pk()
    codigo: Mapped[str] = mapped_column(String(32), unique=True)
    nome: Mapped[str] = mapped_column(String(80))


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (Index("uq_usuarios_email_lower", func.lower(text("email")), unique=True),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    perfil_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("perfis.id"))
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    nome: Mapped[str] = mapped_column(String(180))
    email: Mapped[str] = mapped_column(String(320))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    criado_em: Mapped[datetime] = _ts()
    atualizado_em: Mapped[datetime] = _ts(onupdate=func.now())
    ultimo_login_em: Mapped[datetime | None] = _ts(nullable=True)
    # Login por e-mail e senha (opcional): somente o hash Argon2id é guardado.
    senha_hash: Mapped[str | None] = mapped_column(String(255))
    senha_atualizada_em: Mapped[datetime | None] = _ts(nullable=True)

    perfil: Mapped[Perfil] = relationship(lazy="joined")

    @property
    def papel(self) -> str:
        return self.perfil.codigo


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(String(180))
    nome_fantasia: Mapped[str | None] = mapped_column(String(180))
    documento: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(
        String(24), default="ativo", server_default=text("'ativo'::character varying")
    )
    criado_em: Mapped[datetime] = _ts()
    atualizado_em: Mapped[datetime] = _ts(onupdate=func.now())
    arquivado_em: Mapped[datetime | None] = _ts(nullable=True)

    __table_args__ = (Index("ix_clientes_status_nome", "status", "nome"),)


class UsuarioCliente(Base):
    __tablename__ = "usuarios_clientes"
    __table_args__ = (Index("ix_usuarios_clientes_cliente", "cliente_id"),)

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), primary_key=True
    )
    criado_em: Mapped[datetime] = _ts()


class Integracao(Base):
    __tablename__ = "integracoes"
    __table_args__ = (Index("ix_integracoes_cliente", "cliente_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"))
    plataforma: Mapped[str] = mapped_column(String(32))
    identificador_externo: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(32), default="pendente", server_default=text("'pendente'::character varying")
    )
    # Referência opaca para credenciais_integracao ("secret:<uuid>"); nunca contém token.
    referencia_credencial: Mapped[str | None] = mapped_column(String(255))
    ultima_sincronizacao_em: Mapped[datetime | None] = _ts(nullable=True)
    erro_sincronizacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = _ts()
    atualizado_em: Mapped[datetime] = _ts(onupdate=func.now())
    # 0002
    escopos: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    conectado_por: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    revogada_em: Mapped[datetime | None] = _ts(nullable=True)

    contas: Mapped[list[ContaAnuncio]] = relationship(
        back_populates="integracao", order_by="ContaAnuncio.nome"
    )


class ContaAnuncio(Base):
    __tablename__ = "contas_anuncio"
    __table_args__ = (UniqueConstraint("integracao_id", "conta_externa_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    integracao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("integracoes.id"))
    conta_externa_id: Mapped[str] = mapped_column(String(255))
    nome: Mapped[str] = mapped_column(String(255))
    moeda: Mapped[str] = mapped_column(CHAR(3), default="BRL", server_default=text("'BRL'::bpchar"))
    fuso_horario: Mapped[str] = mapped_column(
        String(100),
        default="America/Sao_Paulo",
        server_default=text("'America/Sao_Paulo'::character varying"),
    )
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    # 0002
    carga_historica_dias: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90, server_default=text("90")
    )
    # Mapeamento explícito de ações → conversões ({"action_types": [...], "janela": ...}).
    # Sem mapeamento, conversões ficam ausentes para evitar equiparação indevida.
    mapeamento_conversoes: Mapped[dict[str, Any]] = _jsonb()
    ultima_sincronizacao_em: Mapped[datetime | None] = _ts(nullable=True)
    dados_ate: Mapped[date | None] = mapped_column(Date)  # freshness: último dia coletado
    criado_em: Mapped[datetime] = _ts()

    integracao: Mapped[Integracao] = relationship(back_populates="contas")


class MetricaDiaria(Base):
    __tablename__ = "metricas_diarias"
    __table_args__ = (
        UniqueConstraint("conta_anuncio_id", "data", "nivel", "entidade_externa_id"),
        Index("ix_metricas_conta_data", "conta_anuncio_id", text("data DESC")),
        Index("ix_metricas_conta_nivel_data", "conta_anuncio_id", "nivel", "data"),
        Index("ix_metricas_campanha", "conta_anuncio_id", "campanha_externa_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    conta_anuncio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contas_anuncio.id"))
    data: Mapped[date] = mapped_column(Date)
    nivel: Mapped[str] = mapped_column(String(24))
    entidade_externa_id: Mapped[str] = mapped_column(String(255))
    impressoes: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text("0"))
    cliques: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text("0"))
    investimento: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=0, server_default=text("0")
    )
    # 0002: NULL = sem mapeamento de conversão (sem default 0).
    conversoes: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    valor_conversoes: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    dados_extras: Mapped[dict[str, Any]] = _jsonb()
    sincronizado_em: Mapped[datetime] = _ts()
    # 0002: identificação da hierarquia (IDs válidos apenas dentro da conta/provedor).
    entidade_nome: Mapped[str | None] = mapped_column(String(400))
    campanha_externa_id: Mapped[str | None] = mapped_column(String(255))
    campanha_nome: Mapped[str | None] = mapped_column(String(400))
    conjunto_externo_id: Mapped[str | None] = mapped_column(String(255))
    conjunto_nome: Mapped[str | None] = mapped_column(String(400))
    # Conversões por tipo de ação/janela, como recebidas do provedor.
    conversoes_detalhe: Mapped[dict[str, Any]] = _jsonb()


class Dashboard(Base):
    __tablename__ = "dashboards"
    __table_args__ = (Index("ix_dashboards_cliente", "cliente_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"))
    criado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    nome: Mapped[str] = mapped_column(String(180))
    # {"descricao": str, "filtros": {...}, "layout": {...}}
    configuracao: Mapped[dict[str, Any]] = _jsonb()
    criado_em: Mapped[datetime] = _ts()
    atualizado_em: Mapped[datetime] = _ts(onupdate=func.now())  # 0002

    widgets: Mapped[list[DashboardWidget]] = relationship(
        back_populates="dashboard",
        cascade="all, delete-orphan",
        order_by="DashboardWidget.posicao",
    )


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"
    __table_args__ = (Index("ix_dashboard_widgets_dashboard", "dashboard_id", "posicao"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    dashboard_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dashboards.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(60))
    posicao: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # {"titulo": str, "kpi": str, "layout": {...}}
    configuracao: Mapped[dict[str, Any]] = _jsonb()

    dashboard: Mapped[Dashboard] = relationship(back_populates="widgets")


class Relatorio(Base):
    __tablename__ = "relatorios"
    __table_args__ = (Index("ix_relatorios_cliente", "cliente_id", "criado_em"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"))
    criado_por: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    titulo: Mapped[str] = mapped_column(String(180))
    # {"template", "periodo", "fontes", "kpis", "graficos", "comentarios", "filtros"}
    configuracao: Mapped[dict[str, Any]] = _jsonb()
    criado_em: Mapped[datetime] = _ts()
    atualizado_em: Mapped[datetime] = _ts(onupdate=func.now())  # 0002
    arquivado_em: Mapped[datetime | None] = _ts(nullable=True)  # 0002: exclusão lógica

    execucoes: Mapped[list[RelatorioExecucao]] = relationship(back_populates="relatorio")


class RelatorioExecucao(Base):
    __tablename__ = "relatorio_execucoes"
    __table_args__ = (
        UniqueConstraint("relatorio_id", "idempotency_key", name="uq_relatorio_execucoes_idem"),
        Index("ix_relatorio_execucoes_relatorio", "relatorio_id", "iniciado_em"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    relatorio_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("relatorios.id"))
    status: Mapped[str] = mapped_column(
        String(24), default="pendente", server_default=text("'pendente'::character varying")
    )
    # Chave opaca no storage privado (nunca caminho da VPS).
    arquivo_referencia: Mapped[str | None] = mapped_column(Text)
    erro: Mapped[str | None] = mapped_column(Text)
    iniciado_em: Mapped[datetime] = _ts()  # baseline: momento da solicitação
    finalizado_em: Mapped[datetime | None] = _ts(nullable=True)
    # 0002
    idempotency_key: Mapped[str | None] = mapped_column(String(200))
    solicitado_por: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    progresso: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    # Filtros, período, horário de corte e última coleta capturados na solicitação.
    snapshot: Mapped[dict[str, Any]] = _jsonb()
    tamanho_bytes: Mapped[int | None] = mapped_column(BigInteger)
    expira_em: Mapped[datetime | None] = _ts(nullable=True)

    relatorio: Mapped[Relatorio] = relationship(back_populates="execucoes")


class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        Index("ix_auditoria_data", text("data_hora DESC")),
        Index("ix_auditoria_cliente_data", "cliente_id", "data_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    acao: Mapped[str] = mapped_column(String(100))
    entidade: Mapped[str] = mapped_column(String(80))
    entidade_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadados: Mapped[dict[str, Any]] = _jsonb()
    data_hora: Mapped[datetime] = _ts()
    # 0002
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clientes.id", ondelete="SET NULL")
    )
    ip: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))


# --- Tabelas novas (0002) -------------------------------------------------


class Sessao(Base):
    __tablename__ = "sessoes"
    __table_args__ = (Index("ix_sessoes_usuario", "usuario_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    # sha256 do token opaco do cookie; o token em si nunca é persistido.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogado_em: Mapped[datetime | None] = _ts(nullable=True)
    criado_em: Mapped[datetime] = _ts()
    ultimo_acesso_em: Mapped[datetime | None] = _ts(nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(400))

    usuario: Mapped[Usuario] = relationship(lazy="joined")


class OAuthState(Base):
    """State/nonce/PKCE de fluxos OAuth (login e integrações), de uso único."""

    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256(state)
    finalidade: Mapped[str] = mapped_column(String(32))  # login | <plataforma>
    nonce: Mapped[str | None] = mapped_column(String(128))
    code_verifier: Mapped[str | None] = mapped_column(String(128))
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE")
    )
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE")
    )
    integracao_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("integracoes.id", ondelete="CASCADE")
    )
    criado_em: Mapped[datetime] = _ts()
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_em: Mapped[datetime | None] = _ts(nullable=True)


class CredencialIntegracao(Base):
    """Credenciais criptografadas (Fernet). A chave fica fora do banco."""

    __tablename__ = "credenciais_integracao"

    id: Mapped[uuid.UUID] = _uuid_pk()
    integracao_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("integracoes.id", ondelete="CASCADE"), unique=True
    )
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    criado_em: Mapped[datetime] = _ts()
    atualizado_em: Mapped[datetime] = _ts(onupdate=func.now())


class SyncJob(Base):
    __tablename__ = "sync_jobs"
    __table_args__ = (
        UniqueConstraint("integracao_id", "idempotency_key", name="uq_sync_jobs_idem"),
        Index("ix_sync_jobs_integracao_criado", "integracao_id", "criado_em"),
        Index("ix_sync_jobs_status", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    integracao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integracoes.id", ondelete="CASCADE")
    )
    conta_anuncio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("contas_anuncio.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    periodo_inicio: Mapped[date] = mapped_column(Date)
    periodo_fim: Mapped[date] = mapped_column(Date)
    tentativa: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    idempotency_key: Mapped[str] = mapped_column(String(200))
    total_registros: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    erro_sanitizado: Mapped[str | None] = mapped_column(Text)
    criado_por: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    proxima_tentativa_em: Mapped[datetime | None] = _ts(nullable=True)
    iniciado_em: Mapped[datetime | None] = _ts(nullable=True)
    finalizado_em: Mapped[datetime | None] = _ts(nullable=True)
    criado_em: Mapped[datetime] = _ts()
