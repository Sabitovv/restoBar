"""store menu item recipe as json array

Revision ID: 20260514_0007
Revises: 20260514_0006
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260514_0007"
down_revision = "20260514_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("recipe_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE menu_items
            SET recipe_json = CASE
                WHEN recipe IS NULL OR btrim(recipe) = '' THEN '[]'::jsonb
                ELSE to_jsonb(
                    array_remove(
                        regexp_split_to_array(regexp_replace(recipe, ',', E'\\n', 'g'), E'\\s*\\n\\s*'),
                        ''
                    )
                )
            END
            """
        )
    )
    op.drop_column("menu_items", "recipe")
    op.alter_column("menu_items", "recipe_json", new_column_name="recipe")


def downgrade() -> None:
    op.add_column("menu_items", sa.Column("recipe_text", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE menu_items
            SET recipe_text = CASE
                WHEN recipe IS NULL THEN NULL
                ELSE array_to_string(ARRAY(SELECT jsonb_array_elements_text(recipe)), E'\n')
            END
            """
        )
    )
    op.drop_column("menu_items", "recipe")
    op.alter_column("menu_items", "recipe_text", new_column_name="recipe")
