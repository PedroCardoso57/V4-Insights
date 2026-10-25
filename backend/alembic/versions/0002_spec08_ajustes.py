"""SPEC-08: sessões, sync_jobs, credenciais, auditoria por cliente e campos incrementais.

Incremental sobre a baseline: não altera nem remove dados existentes (exceto ajustes de
domínio documentados abaixo) e é reversível.

- clientes.status ganha 'arquivado' (linhas com arquivado_em passam a 'arquivado').
- integracoes.status ganha 'pausada'.
- metricas_diarias.conversoes/valor_conversoes passam a aceitar NULL (= sem mapeamento) e
  perdem o default 0; valores existentes são preservados.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB_VAZIO = sa.text("'{}'::jsonb")
UUID_DEFAULT = sa.text("gen_random_uuid()")


def _ts(nome: str, nullable: bool = True) -> sa.Column:  # type: ignore[type-arg]
    if nullable:
        return sa.Column(nome, sa.DateTime(timezone=True), nullable=True)
    return sa.Column(nome, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    # clientes ---------------------------------------------------------------
    op.drop_constraint("clientes_status_check", "clientes", type_="check")
    op.execute("UPDATE clientes SET status = 'arquivado' WHERE arquivado_em IS NOT NULL")
    op.create_check_constraint(
        "ck_clientes_status", "clientes", "status IN ('ativo','inativo','arquivado')"
    )
    op.create_index("ix_clientes_status_nome", "clientes", ["status", "nome"])
    op.create_index("ix_usuarios_clientes_cliente", "usuarios_clientes", ["cliente_id"])

    # integracoes ------------------------------------------------------------
    op.drop_constraint("integracoes_status_check", "integracoes", type_="check")
    op.create_check_constraint(
        "ck_integracoes_status",
        "integracoes",
        "status IN ('pendente','conectada','pausada','erro','revogada')",
    )
    op.add_column(
        "integracoes",
        sa.Column("escopos", pg.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("integracoes", sa.Column("conectado_por", pg.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_integracoes_conectado_por",
        "integracoes",
        "usuarios",
        ["conectado_por"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("integracoes", _ts("revogada_em"))

    # contas_anuncio ---------------------------------------------------------
    op.add_column(
        "contas_anuncio",
        sa.Column(
            "carga_historica_dias", sa.Integer(), nullable=False, server_default=sa.text("90")
        ),
    )
    op.add_column(
        "contas_anuncio",
        sa.Column("mapeamento_conversoes", pg.JSONB(), nullable=False, server_default=JSONB_VAZIO),
    )
    op.add_column("contas_anuncio", _ts("ultima_sincronizacao_em"))
    op.add_column("contas_anuncio", sa.Column("dados_ate", sa.Date(), nullable=True))
    op.add_column("contas_anuncio", _ts("criado_em", nullable=False))

    # metricas_diarias -------------------------------------------------------
    # NULL passa a significar "sem mapeamento de conversão": remove o default 0.
    op.alter_column("metricas_diarias", "conversoes", nullable=True, server_default=None)
    op.alter_column("metricas_diarias", "valor_conversoes", nullable=True, server_default=None)
    for nome, tamanho in (
        ("entidade_nome", 400),
        ("campanha_externa_id", 255),
        ("campanha_nome", 400),
        ("conjunto_externo_id", 255),
        ("conjunto_nome", 400),
    ):
        op.add_column("metricas_diarias", sa.Column(nome, sa.String(tamanho), nullable=True))
    op.add_column(
        "metricas_diarias",
        sa.Column("conversoes_detalhe", pg.JSONB(), nullable=False, server_default=JSONB_VAZIO),
    )
    op.create_index(
        "ix_metricas_conta_nivel_data", "metricas_diarias", ["conta_anuncio_id", "nivel", "data"]
    )
    op.create_index(
        "ix_metricas_campanha", "metricas_diarias", ["conta_anuncio_id", "campanha_externa_id"]
    )

    # dashboards / relatórios -----------------------------------------------
    op.add_column("dashboards", _ts("atualizado_em", nullable=False))
    op.create_index("ix_dashboards_cliente", "dashboards", ["cliente_id"])
    op.create_index(
        "ix_dashboard_widgets_dashboard", "dashboard_widgets", ["dashboard_id", "posicao"]
    )
    op.add_column("relatorios", _ts("atualizado_em", nullable=False))
    # Exclusão lógica: execuções e PDFs permanecem no histórico.
    op.add_column("relatorios", _ts("arquivado_em"))
    op.create_index("ix_relatorios_cliente", "relatorios", ["cliente_id", "criado_em"])

    op.add_column("relatorio_execucoes", sa.Column("idempotency_key", sa.String(200)))
    op.add_column(
        "relatorio_execucoes", sa.Column("solicitado_por", pg.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_relatorio_execucoes_solicitado_por",
        "relatorio_execucoes",
        "usuarios",
        ["solicitado_por"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "relatorio_execucoes",
        sa.Column("progresso", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "relatorio_execucoes",
        sa.Column("snapshot", pg.JSONB(), nullable=False, server_default=JSONB_VAZIO),
    )
    op.add_column("relatorio_execucoes", sa.Column("tamanho_bytes", sa.BigInteger()))
    op.add_column("relatorio_execucoes", _ts("expira_em"))
    op.create_unique_constraint(
        "uq_relatorio_execucoes_idem", "relatorio_execucoes", ["relatorio_id", "idempotency_key"]
    )
    op.create_index(
        "ix_relatorio_execucoes_relatorio", "relatorio_execucoes", ["relatorio_id", "iniciado_em"]
    )

    # auditoria --------------------------------------------------------------
    op.add_column("auditoria", sa.Column("cliente_id", pg.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_auditoria_cliente", "auditoria", "clientes", ["cliente_id"], ["id"], ondelete="SET NULL"
    )
    op.add_column("auditoria", sa.Column("ip", sa.String(64)))
    op.add_column("auditoria", sa.Column("request_id", sa.String(64)))
    op.create_index("ix_auditoria_cliente_data", "auditoria", ["cliente_id", "data_hora"])

    # tabelas novas ----------------------------------------------------------
    op.create_table(
        "sessoes",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "usuario_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        _ts("revogado_em"),
        _ts("criado_em", nullable=False),
        _ts("ultimo_acesso_em"),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(400)),
    )
    op.create_index("ix_sessoes_usuario", "sessoes", ["usuario_id"])

    op.create_table(
        "oauth_states",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("finalidade", sa.String(32), nullable=False),
        sa.Column("nonce", sa.String(128)),
        sa.Column("code_verifier", sa.String(128)),
        sa.Column(
            "usuario_id", pg.UUID(as_uuid=True), sa.ForeignKey("usuarios.id", ondelete="CASCADE")
        ),
        sa.Column(
            "cliente_id", pg.UUID(as_uuid=True), sa.ForeignKey("clientes.id", ondelete="CASCADE")
        ),
        sa.Column(
            "integracao_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("integracoes.id", ondelete="CASCADE"),
        ),
        _ts("criado_em", nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        _ts("usado_em"),
    )

    op.create_table(
        "credenciais_integracao",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "integracao_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("integracoes.id", ondelete="CASCADE"),
            unique=True,
        ),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        _ts("criado_em", nullable=False),
        _ts("atualizado_em", nullable=False),
    )

    op.create_table(
        "sync_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "integracao_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("integracoes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conta_anuncio_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("contas_anuncio.id", ondelete="CASCADE"),
        ),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("periodo_inicio", sa.Date(), nullable=False),
        sa.Column("periodo_fim", sa.Date(), nullable=False),
        sa.Column("tentativa", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("total_registros", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("erro_sanitizado", sa.Text()),
        sa.Column(
            "criado_por", pg.UUID(as_uuid=True), sa.ForeignKey("usuarios.id", ondelete="SET NULL")
        ),
        _ts("proxima_tentativa_em"),
        _ts("iniciado_em"),
        _ts("finalizado_em"),
        _ts("criado_em", nullable=False),
        sa.UniqueConstraint("integracao_id", "idempotency_key", name="uq_sync_jobs_idem"),
        sa.CheckConstraint(
            "tipo IN ('historico','incremental','manual')", name="ck_sync_jobs_tipo"
        ),
        sa.CheckConstraint(
            "status IN ('pendente','executando','sucesso','erro','cancelado')",
            name="ck_sync_jobs_status",
        ),
        sa.CheckConstraint("periodo_inicio <= periodo_fim", name="ck_sync_jobs_periodo"),
    )
    op.create_index("ix_sync_jobs_integracao_criado", "sync_jobs", ["integracao_id", "criado_em"])
    op.create_index("ix_sync_jobs_status", "sync_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("sync_jobs")
    op.drop_table("credenciais_integracao")
    op.drop_table("oauth_states")
    op.drop_table("sessoes")

    op.drop_index("ix_auditoria_cliente_data", "auditoria")
    op.drop_constraint("fk_auditoria_cliente", "auditoria", type_="foreignkey")
    for c in ("request_id", "ip", "cliente_id"):
        op.drop_column("auditoria", c)

    op.drop_index("ix_relatorio_execucoes_relatorio", "relatorio_execucoes")
    op.drop_constraint("uq_relatorio_execucoes_idem", "relatorio_execucoes", type_="unique")
    op.drop_constraint(
        "fk_relatorio_execucoes_solicitado_por", "relatorio_execucoes", type_="foreignkey"
    )
    for c in (
        "expira_em",
        "tamanho_bytes",
        "snapshot",
        "progresso",
        "solicitado_por",
        "idempotency_key",
    ):
        op.drop_column("relatorio_execucoes", c)
    op.drop_index("ix_relatorios_cliente", "relatorios")
    op.drop_column("relatorios", "arquivado_em")
    op.drop_column("relatorios", "atualizado_em")
    op.drop_index("ix_dashboard_widgets_dashboard", "dashboard_widgets")
    op.drop_index("ix_dashboards_cliente", "dashboards")
    op.drop_column("dashboards", "atualizado_em")

    op.drop_index("ix_metricas_campanha", "metricas_diarias")
    op.drop_index("ix_metricas_conta_nivel_data", "metricas_diarias")
    for c in (
        "conversoes_detalhe",
        "conjunto_nome",
        "conjunto_externo_id",
        "campanha_nome",
        "campanha_externa_id",
        "entidade_nome",
    ):
        op.drop_column("metricas_diarias", c)
    op.execute("UPDATE metricas_diarias SET conversoes = 0 WHERE conversoes IS NULL")
    op.execute("UPDATE metricas_diarias SET valor_conversoes = 0 WHERE valor_conversoes IS NULL")
    op.alter_column("metricas_diarias", "conversoes", nullable=False, server_default=sa.text("0"))
    op.alter_column(
        "metricas_diarias", "valor_conversoes", nullable=False, server_default=sa.text("0")
    )

    for c in (
        "criado_em",
        "dados_ate",
        "ultima_sincronizacao_em",
        "mapeamento_conversoes",
        "carga_historica_dias",
    ):
        op.drop_column("contas_anuncio", c)

    op.drop_column("integracoes", "revogada_em")
    op.drop_constraint("fk_integracoes_conectado_por", "integracoes", type_="foreignkey")
    op.drop_column("integracoes", "conectado_por")
    op.drop_column("integracoes", "escopos")
    op.drop_constraint("ck_integracoes_status", "integracoes", type_="check")
    op.execute("UPDATE integracoes SET status = 'conectada' WHERE status = 'pausada'")
    op.create_check_constraint(
        "integracoes_status_check",
        "integracoes",
        "status IN ('pendente','conectada','erro','revogada')",
    )

    op.drop_index("ix_usuarios_clientes_cliente", "usuarios_clientes")
    op.drop_index("ix_clientes_status_nome", "clientes")
    op.drop_constraint("ck_clientes_status", "clientes", type_="check")
    op.execute("UPDATE clientes SET status = 'inativo' WHERE status = 'arquivado'")
    op.create_check_constraint("clientes_status_check", "clientes", "status IN ('ativo','inativo')")
