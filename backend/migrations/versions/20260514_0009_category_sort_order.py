"""add sort order for menu categories

Revision ID: 20260514_0009
Revises: 20260514_0008
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_0009"
down_revision = "20260514_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_categories", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.execute(sa.text("""
        WITH ranked AS (
          SELECT id, row_number() OVER (PARTITION BY restaurant_id ORDER BY created_at, id) AS rn
          FROM menu_categories
        )
        UPDATE menu_categories c
        SET sort_order = ranked.rn
        FROM ranked
        WHERE c.id = ranked.id
    """))
    op.alter_column("menu_categories", "sort_order", server_default=None)


def downgrade() -> None:
    op.drop_column("menu_categories", "sort_order")
