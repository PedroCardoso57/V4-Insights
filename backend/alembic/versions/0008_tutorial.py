"""Tutorial de primeiro acesso.

`usuarios.tutorial_visto_em` fica vazio até o colaborador concluir ou pular o tour guiado
do Nico; enquanto estiver vazio, o app abre o tutorial no próximo acesso. Incremental e
reversível.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usuarios", sa.Column("tutorial_visto_em", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("usuarios", "tutorial_visto_em")
