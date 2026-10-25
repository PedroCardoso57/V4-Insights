"""Baseline: reproduz exatamente backend/migrations/001_initial.sql (pacote Sprint 1).

Bases que já receberam o SQL manualmente NÃO devem executar esta revisão; o comando
`python -m app.db.migrate` detecta esse caso e apenas registra (`stamp`) a revisão 0001.

Revision ID: 0001
Revises:
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BASELINE = Path(__file__).resolve().parent.parent / "baseline" / "001_initial.sql"
BASELINE_TABLES = (
    "perfis",
    "usuarios",
    "clientes",
    "usuarios_clientes",
    "integracoes",
    "contas_anuncio",
    "metricas_diarias",
    "dashboards",
    "dashboard_widgets",
    "relatorios",
    "relatorio_execucoes",
    "auditoria",
)


def upgrade() -> None:
    existentes = set(sa.inspect(op.get_bind()).get_table_names()) & set(BASELINE_TABLES)
    if existentes:
        raise RuntimeError(
            "Tabelas da baseline já existem sem registro do Alembic ("
            + ", ".join(sorted(existentes))
            + "). Use `python -m app.db.migrate`, que valida e registra a baseline."
        )
    sql = BASELINE.read_text(encoding="utf-8")
    # A transação é controlada pelo Alembic; remove BEGIN/COMMIT do arquivo original.
    corpo = "\n".join(
        linha for linha in sql.splitlines() if linha.strip().upper() not in ("BEGIN;", "COMMIT;")
    )
    op.get_bind().exec_driver_sql(corpo)


def downgrade() -> None:
    for tabela in reversed(BASELINE_TABLES):
        op.execute(f'DROP TABLE IF EXISTS "{tabela}" CASCADE')
