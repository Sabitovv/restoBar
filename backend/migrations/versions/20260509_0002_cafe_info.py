"""add cafe_info table

Revision ID: 20260509_0002
Revises: 20260509_0001
Create Date: 2026-05-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260509_0002"
down_revision = "20260509_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cafe_info",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("cafe_info")
