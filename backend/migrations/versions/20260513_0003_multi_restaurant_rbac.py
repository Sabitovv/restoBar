"""multi restaurant and rbac foundation

Revision ID: 20260513_0003
Revises: 20260509_0002
Create Date: 2026-05-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260513_0003"
down_revision = "20260509_0002"
branch_labels = None
depends_on = None


MAIN_RESTAURANT_ID = "11111111-1111-1111-1111-111111111111"

staff_role_enum = sa.Enum("super_admin", "admin", "manager", name="staffrole")
membership_status_enum = sa.Enum("invited", "active", "revoked", name="membershipstatus")


def upgrade() -> None:
    op.create_table(
        "restaurants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO restaurants (id, name, slug, is_active, created_at, updated_at)
            VALUES (CAST(:id AS uuid), :name, :slug, :is_active, now(), now())
            """
        ).bindparams(id=MAIN_RESTAURANT_ID, name="Main Restaurant", slug="main", is_active=True)
    )

    op.add_column(
        "menu_categories",
        sa.Column(
            "restaurant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            server_default=MAIN_RESTAURANT_ID,
        ),
    )
    op.add_column(
        "menu_items",
        sa.Column(
            "restaurant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            server_default=MAIN_RESTAURANT_ID,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE menu_categories SET restaurant_id = CAST(:restaurant_id AS uuid) WHERE restaurant_id IS NULL"
        ).bindparams(restaurant_id=MAIN_RESTAURANT_ID)
    )
    op.execute(
        sa.text("UPDATE menu_items SET restaurant_id = CAST(:restaurant_id AS uuid) WHERE restaurant_id IS NULL").bindparams(
            restaurant_id=MAIN_RESTAURANT_ID
        )
    )
    op.alter_column("menu_categories", "restaurant_id", nullable=False, server_default=None)
    op.alter_column("menu_items", "restaurant_id", nullable=False, server_default=None)

    op.create_foreign_key("fk_menu_categories_restaurant", "menu_categories", "restaurants", ["restaurant_id"], ["id"])
    op.create_foreign_key("fk_menu_items_restaurant", "menu_items", "restaurants", ["restaurant_id"], ["id"])
    op.create_index("ix_menu_categories_restaurant_active", "menu_categories", ["restaurant_id", "is_active"], unique=False)
    op.create_index("ix_menu_items_restaurant_active", "menu_items", ["restaurant_id", "is_active"], unique=False)

    op.create_table(
        "staff_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("role", staff_role_enum, nullable=False),
        sa.Column("status", membership_status_enum, nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "telegram_user_id", name="uq_staff_membership_restaurant_telegram_user"),
    )
    op.create_index("ix_staff_memberships_role_status", "staff_memberships", ["role", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_staff_memberships_role_status", table_name="staff_memberships")
    op.drop_table("staff_memberships")

    op.drop_index("ix_menu_items_restaurant_active", table_name="menu_items")
    op.drop_index("ix_menu_categories_restaurant_active", table_name="menu_categories")
    op.drop_constraint("fk_menu_items_restaurant", "menu_items", type_="foreignkey")
    op.drop_constraint("fk_menu_categories_restaurant", "menu_categories", type_="foreignkey")
    op.drop_column("menu_items", "restaurant_id")
    op.drop_column("menu_categories", "restaurant_id")

    op.drop_table("restaurants")
    membership_status_enum.drop(op.get_bind(), checkfirst=False)
    staff_role_enum.drop(op.get_bind(), checkfirst=False)
