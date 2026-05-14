"""add client theme and menu metadata fields

Revision ID: 20260514_0012
Revises: 20260514_0011
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260514_0012"
down_revision = "20260514_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_categories", sa.Column("icon", sa.Text(), nullable=True))
    op.add_column("menu_categories", sa.Column("background_color", sa.String(length=32), nullable=True))

    op.add_column("menu_items", sa.Column("is_popular", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("menu_items", "is_popular", server_default=None)

    op.add_column("menu_item_variants", sa.Column("weight", sa.String(length=64), nullable=True))

    op.create_table(
        "client_themes",
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("restaurant_id"),
    )


def downgrade() -> None:
    op.drop_table("client_themes")
    op.drop_column("menu_item_variants", "weight")
    op.drop_column("menu_items", "is_popular")
    op.drop_column("menu_categories", "background_color")
    op.drop_column("menu_categories", "icon")
