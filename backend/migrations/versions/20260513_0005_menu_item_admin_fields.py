"""add recipe and availability fields for menu items

Revision ID: 20260513_0005
Revises: 20260513_0004
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260513_0005"
down_revision = "20260513_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("recipe", sa.Text(), nullable=True))
    op.add_column("menu_items", sa.Column("is_available_now", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column("menu_items", "is_available_now", server_default=None)


def downgrade() -> None:
    op.drop_column("menu_items", "is_available_now")
    op.drop_column("menu_items", "recipe")
