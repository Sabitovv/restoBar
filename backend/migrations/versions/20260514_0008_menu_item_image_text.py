"""expand menu item image column to text

Revision ID: 20260514_0008
Revises: 20260514_0007
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260514_0008"
down_revision = "20260514_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("menu_items", "image", existing_type=sa.String(length=512), type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("menu_items", "image", existing_type=sa.Text(), type_=sa.String(length=512), existing_nullable=True)
