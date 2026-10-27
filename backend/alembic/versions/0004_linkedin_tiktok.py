"""Integrações LinkedIn Ads e TikTok Ads: amplia as plataformas aceitas.

Incremental e reversível. O downgrade falha se já houver integrações dessas
plataformas (remova-as antes), para não apagar dados silenciosamente.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("integracoes_plataforma_check", "integracoes", type_="check")
    op.create_check_constraint(
        "ck_integracoes_plataforma",
        "integracoes",
        "plataforma IN ('meta_ads','google_ads','linkedin_ads','tiktok_ads')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_integracoes_plataforma", "integracoes", type_="check")
    op.create_check_constraint(
        "integracoes_plataforma_check",
        "integracoes",
        "plataforma IN ('meta_ads','google_ads')",
    )
