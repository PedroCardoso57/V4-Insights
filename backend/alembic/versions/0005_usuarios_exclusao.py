"""Exclusão de colaboradores pela tela de Usuários.

O colaborador excluído é anonimizado (LGPD) e marcado com `excluido_em`; a linha permanece
para manter a integridade de dashboards, relatórios e da trilha de auditoria que o referenciam.
Incremental e reversível.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("excluido_em", sa.DateTime(timezone=True), nullable=True))
    # Quem já foi anonimizado pela CLI de LGPD conta como excluído.
    op.execute(
        "UPDATE usuarios SET excluido_em = atualizado_em "
        "WHERE email LIKE 'removido+%@anonimizado.invalid'"
    )


def downgrade() -> None:
    op.drop_column("usuarios", "excluido_em")
