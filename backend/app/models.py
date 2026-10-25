"""Modelos ORM. O schema é versionado exclusivamente por Alembic (migrations/)."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Papel(enum.StrEnum):
    admin = "admin"
    gestor = "gestor"
    analista = "analista"
    visualizador = "visualizador"


class StatusCliente(enum.StrEnum):
    ativo = "ativo"
    arquivado = "arquivado"


class Plataforma(enum.StrEnum):
    meta = "meta"
    google_ads = "google_ads"


class StatusIntegracao(enum.StrEnum):
    pendente = "pendente"  # autorizada, aguardando seleção de contas
    ativa = "ativa"
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
    campanha = "campanha"
    conjunto = "conjunto"
    anuncio = "anuncio"


def _check(col: str, enum_cls: type[enum.StrEnum], name: str) -> CheckConstraint:
    values = ", ".join(f"'{v.value}'" for v in enum_cls)
    return CheckConstraint(f"{col} IN ({values})", name=name)


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now_col(**kw: Any) -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), **kw)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (_check("papel", Papel, "ck_usuarios_papel"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    papel: Mapped[str] = mapped_column(String(20))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    ultimo_login_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = _now_col()
    atualizado_em: Mapped[datetime] = _now_col(onupdate=func.now())


class Sessao(Base):
    __tablename__ = "sessoes"

    # sha256 do token opaco enviado no cookie — o token em si nunca é persistido.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    csrf_token: Mapped[str] = mapped_column(String(64))
    criado_em: Mapped[datetime] = _now_col()
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(400))

    usuario: Mapped[Usuario] = relationship(lazy="joined")


class OAuthState(Base):
    """State de fluxos OAuth (login interno e conexões de integrações), uso único."""

    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256(state)
    finalidade: Mapped[str] = mapped_column(String(30))  # login | meta | google_ads
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
    criado_em: Mapped[datetime] = _now_col()
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Cliente(Base):
    __tablename__ = "clientes"
    __table_args__ = (_check("status", StatusCliente, "ck_clientes_status"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    nome: Mapped[str] = mapped_column(String(160), index=True)
    nome_fantasia: Mapped[str | None] = mapped_column(String(160))
    documento: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="ativo", server_default="ativo")
    criado_em: Mapped[datetime] = _now_col()
    atualizado_em: Mapped[datetime] = _now_col(onupdate=func.now())
    arquivado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsuarioCliente(Base):
    __tablename__ = "usuarios_clientes"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    criado_em: Mapped[datetime] = _now_col()


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), index=True
    )
    acao: Mapped[str] = mapped_column(String(60))
    entidade: Mapped[str] = mapped_column(String(60))
    entidade_id: Mapped[str | None] = mapped_column(String(64))
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clientes.id", ondelete="SET NULL"), index=True
    )
    dados: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    ip: Mapped[str | None] = mapped_column(String(64))
    criado_em: Mapped[datetime] = _now_col(index=True)


class Segredo(Base):
    """Credenciais criptografadas (Fernet). A chave fica fora do banco."""

    __tablename__ = "segredos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    criado_em: Mapped[datetime] = _now_col()
    atualizado_em: Mapped[datetime] = _now_col(onupdate=func.now())


class Integracao(Base):
    __tablename__ = "integracoes"
    __table_args__ = (
        _check("plataforma", Plataforma, "ck_integracoes_plataforma"),
        _check("status", StatusIntegracao, "ck_integracoes_status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"), index=True
    )
    plataforma: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    # Referência opaca para o segredo (ex.: "secret:<uuid>"); nunca contém o token.
    referencia_credencial: Mapped[str | None] = mapped_column(String(200))
    escopos: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    conectado_por: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    ultimo_erro: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = _now_col()
    atualizado_em: Mapped[datetime] = _now_col(onupdate=func.now())
    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contas: Mapped[list[ContaAnuncio]] = relationship(back_populates="integracao")


class ContaAnuncio(Base):
    __tablename__ = "contas_anuncio"
    __table_args__ = (UniqueConstraint("integracao_id", "id_externo", name="uq_contas_externo"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    integracao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integracoes.id", ondelete="RESTRICT"), index=True
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"), index=True
    )
    id_externo: Mapped[str] = mapped_column(String(64))
    nome: Mapped[str] = mapped_column(String(255))
    moeda: Mapped[str | None] = mapped_column(String(3))
    fuso: Mapped[str | None] = mapped_column(String(64))
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    carga_historica_dias: Mapped[int] = mapped_column(Integer, default=90, server_default="90")
    # Mapeamento explícito de ações → "conversões" (ex.: Meta action_types e janela).
    # Sem mapeamento, conversões ficam ausentes para evitar equiparação indevida.
    mapeamento_conversoes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    ultima_sincronizacao_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dados_ate: Mapped[date | None] = mapped_column(Date)  # freshness: último dia coletado
    criado_em: Mapped[datetime] = _now_col()

    integracao: Mapped[Integracao] = relationship(back_populates="contas")


class SyncJob(Base):
    __tablename__ = "sync_jobs"
    __table_args__ = (
        _check("tipo", TipoJob, "ck_sync_jobs_tipo"),
        _check("status", StatusJob, "ck_sync_jobs_status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    integracao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("integracoes.id", ondelete="CASCADE"), index=True
    )
    conta_anuncio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contas_anuncio.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date] = mapped_column(Date)
    linhas: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tentativas: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    erro: Mapped[str | None] = mapped_column(Text)
    criado_por: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proxima_tentativa_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = _now_col(index=True)


class MetricaDiaria(Base):
    __tablename__ = "metricas_diarias"
    __table_args__ = (
        UniqueConstraint(
            "conta_anuncio_id", "data", "nivel", "entidade_externa_id", name="uq_metricas_chave"
        ),
        _check("nivel", Nivel, "ck_metricas_nivel"),
        Index("ix_metricas_cliente_nivel_data", "cliente_id", "nivel", "data"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conta_anuncio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contas_anuncio.id", ondelete="RESTRICT")
    )
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id", ondelete="RESTRICT"))
    plataforma: Mapped[str] = mapped_column(String(20))
    data: Mapped[date] = mapped_column(Date)
    nivel: Mapped[str] = mapped_column(String(20))
    entidade_externa_id: Mapped[str] = mapped_column(String(64))
    entidade_nome: Mapped[str | None] = mapped_column(String(400))
    campanha_externa_id: Mapped[str | None] = mapped_column(String(64))
    campanha_nome: Mapped[str | None] = mapped_column(String(400))
    moeda: Mapped[str | None] = mapped_column(String(3))
    investimento: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    impressoes: Mapped[int] = mapped_column(BigInteger, default=0)
    cliques: Mapped[int] = mapped_column(BigInteger, default=0)
    conversoes: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    valor_conversoes: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    # Conversões por tipo de ação/atribuição, como recebidas do provedor.
    conversoes_detalhe: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    extras: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    atualizado_em: Mapped[datetime] = _now_col(onupdate=func.now())


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[uuid.UUID] = _uuid_pk()
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clientes.id", ondelete="RESTRICT"), index=True
    )
    nome: Mapped[str] = mapped_column(String(160))
    descricao: Mapped[str | None] = mapped_column(String(500))
    filtros: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    layout: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    criado_por: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL")
    )
    criado_em: Mapped[datetime] = _now_col()
    atualizado_em: Mapped[datetime] = _now_col(onupdate=func.now())

    widgets: Mapped[list[Widget]] = relationship(
        back_populates="dashboard", cascade="all, delete-orphan", order_by="Widget.ordem"
    )


class Widget(Base):
    __tablename__ = "widgets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(30))  # kpi | serie | tabela_campanhas
    titulo: Mapped[str] = mapped_column(String(160))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    posicao: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    ordem: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    criado_em: Mapped[datetime] = _now_col()

    dashboard: Mapped[Dashboard] = relationship(back_populates="widgets")
