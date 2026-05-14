"""allow nullable telegram id for invited staff

Revision ID: 20260513_0004
Revises: 20260513_0003
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260513_0004"
down_revision = "20260513_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("staff_memberships", "telegram_user_id", existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM staff_memberships WHERE telegram_user_id IS NULL"))
    op.alter_column("staff_memberships", "telegram_user_id", existing_type=sa.BigInteger(), nullable=False)
