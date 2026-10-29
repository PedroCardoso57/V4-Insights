"""Foto de perfil dos colaboradores.

A imagem fica numa tabela própria para não pesar nas consultas de usuários; a coluna
`usuarios.foto_atualizada_em` indica que há foto e versiona a URL. Incremental e reversível.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuarios", sa.Column("foto_atualizada_em", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "usuario_fotos",
        sa.Column(
            "usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("conteudo", sa.LargeBinary(), nullable=False),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("usuario_fotos")
    op.drop_column("usuarios", "foto_atualizada_em")
