"""add image field to menu categories

Revision ID: 20260514_0010
Revises: 20260514_0009
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_0010"
down_revision = "20260514_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_categories", sa.Column("image", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("menu_categories", "image")
