"""add restaurant profile fields

Revision ID: 20260514_0011
Revises: 20260514_0010
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260514_0011"
down_revision = "20260514_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("restaurants", sa.Column("about", sa.Text(), nullable=True))
    op.add_column("restaurants", sa.Column("preview_image", sa.Text(), nullable=True))
    op.add_column("restaurants", sa.Column("working_hours_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("restaurants", "working_hours_json")
    op.drop_column("restaurants", "preview_image")
    op.drop_column("restaurants", "about")
