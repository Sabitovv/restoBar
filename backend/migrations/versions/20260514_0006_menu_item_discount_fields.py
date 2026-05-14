"""add fixed discount fields to menu items

Revision ID: 20260514_0006
Revises: 20260513_0005
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_0006"
down_revision = "20260513_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("discount_minor", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("menu_items", sa.Column("discount_is_active", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("menu_items", "discount_minor", server_default=None)
    op.alter_column("menu_items", "discount_is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("menu_items", "discount_is_active")
    op.drop_column("menu_items", "discount_minor")
