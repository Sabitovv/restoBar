"""set menu_items.is_popular default false

Revision ID: 20260515_0013
Revises: 20260514_0012
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20260515_0013"
down_revision = "20260514_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE menu_items SET is_popular = false WHERE is_popular IS NULL")
    op.alter_column("menu_items", "is_popular", existing_type=sa.Boolean(), server_default=sa.false(), nullable=False)


def downgrade() -> None:
    op.alter_column("menu_items", "is_popular", existing_type=sa.Boolean(), server_default=None, nullable=False)
