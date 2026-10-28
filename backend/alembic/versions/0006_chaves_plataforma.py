"""Chaves dos apps das plataformas cadastradas pela tela de Configurações.

Guarda client IDs e segredos (cifrados com ENCRYPTION_KEY) que antes só podiam ir no `.env`.
Incremental e reversível.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chaves_plataforma",
        sa.Column("chave", sa.String(length=64), primary_key=True),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column(
            "atualizado_por",
            sa.Uuid(),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("chaves_plataforma")
