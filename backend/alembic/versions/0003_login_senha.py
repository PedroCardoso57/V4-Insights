"""Login por e-mail e senha: hash Argon2id opcional por usuário.

Incremental e reversível; usuários existentes continuam sem senha (somente Google).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("senha_hash", sa.String(255), nullable=True))
    op.add_column(
        "usuarios", sa.Column("senha_atualizada_em", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("usuarios", "senha_atualizada_em")
    op.drop_column("usuarios", "senha_hash")
