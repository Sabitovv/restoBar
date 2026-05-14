"""add i18n fields, multi-currency prices and strict schedule

Revision ID: 20260514_0013
Revises: 20260514_0012
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260514_0013"
down_revision = "20260514_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("restaurants", sa.Column("about_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("menu_categories", sa.Column("name_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("menu_items", sa.Column("name_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("menu_items", sa.Column("description_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("menu_items", sa.Column("recipe_i18n", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("menu_items", sa.Column("price_by_currency", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.execute(sa.text("UPDATE restaurants SET about_i18n = jsonb_build_object('ru', COALESCE(about, ''))"))
    op.execute(sa.text("UPDATE menu_categories SET name_i18n = jsonb_build_object('ru', COALESCE(name, ''))"))
    op.execute(sa.text("UPDATE menu_items SET name_i18n = jsonb_build_object('ru', COALESCE(name, ''))"))
    op.execute(sa.text("UPDATE menu_items SET description_i18n = jsonb_build_object('ru', COALESCE(description, ''))"))
    op.execute(sa.text("UPDATE menu_items SET recipe_i18n = jsonb_build_object('ru', COALESCE(recipe, '[]'::jsonb))"))
    op.execute(
        sa.text(
            """
            UPDATE menu_items mi
            SET price_by_currency = jsonb_build_object(
                'KZT', COALESCE((
                    SELECT mv.price_minor FROM menu_item_variants mv
                    WHERE mv.menu_item_id = mi.id
                    ORDER BY mv.id ASC
                    LIMIT 1
                ), 0)
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE restaurants
            SET working_hours_json = jsonb_build_object(
                'mon', jsonb_build_object('isOpen', true, 'openAt', '', 'closeAt', ''),
                'tue', jsonb_build_object('isOpen', true, 'openAt', '', 'closeAt', ''),
                'wed', jsonb_build_object('isOpen', true, 'openAt', '', 'closeAt', ''),
                'thu', jsonb_build_object('isOpen', true, 'openAt', '', 'closeAt', ''),
                'fri', jsonb_build_object('isOpen', true, 'openAt', '', 'closeAt', ''),
                'sat', jsonb_build_object('isOpen', true, 'openAt', '', 'closeAt', ''),
                'sun', jsonb_build_object('isOpen', true, 'openAt', '', 'closeAt', '')
            )
            WHERE working_hours_json IS NULL OR jsonb_typeof(working_hours_json) != 'object'
            """
        )
    )


def downgrade() -> None:
    op.drop_column("menu_items", "price_by_currency")
    op.drop_column("menu_items", "recipe_i18n")
    op.drop_column("menu_items", "description_i18n")
    op.drop_column("menu_items", "name_i18n")
    op.drop_column("menu_categories", "name_i18n")
    op.drop_column("restaurants", "about_i18n")
