"""create listings and listing_photos tables

Revision ID: a1b2c3d4e5f6
Revises: fcffeff13bff
Create Date: 2026-08-02 21:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "fcffeff13bff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "transaction_type",
            sa.Enum(
                "vente",
                "location",
                "colocation",
                "vacances",
                name="transaction_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "property_type",
            sa.Enum(
                "appartement",
                "villa",
                "maison",
                "studio",
                "local_commercial",
                "terrain",
                "bureau",
                "immeuble",
                name="property_type",
            ),
            nullable=False,
        ),
        sa.Column("price", sa.BigInteger(), nullable=False),
        sa.Column(
            "price_unit",
            sa.Enum("DZD_total", "DZD_month", "DZD_night", name="price_unit"),
            nullable=False,
        ),
        sa.Column("surface", sa.Integer(), nullable=True),
        sa.Column("rooms", sa.Integer(), nullable=True),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("furnished", sa.Boolean(), nullable=False),
        sa.Column("amenities", sa.JSON(), nullable=False),
        sa.Column("wilaya", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("neighbourhood", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "published",
                "moderated",
                "archived",
                name="listing_status",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_listings_owner_id"), "listings", ["owner_id"])
    op.create_index(op.f("ix_listings_wilaya"), "listings", ["wilaya"])
    op.create_index(op.f("ix_listings_status"), "listings", ["status"])
    op.create_index(
        "ix_listings_filter",
        "listings",
        ["status", "transaction_type", "property_type", "wilaya", "price"],
    )

    op.create_table(
        "listing_photos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("is_cover", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_listing_photos_listing_id"), "listing_photos", ["listing_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_listing_photos_listing_id"), table_name="listing_photos")
    op.drop_table("listing_photos")
    op.drop_index("ix_listings_filter", table_name="listings")
    op.drop_index(op.f("ix_listings_status"), table_name="listings")
    op.drop_index(op.f("ix_listings_wilaya"), table_name="listings")
    op.drop_index(op.f("ix_listings_owner_id"), table_name="listings")
    op.drop_table("listings")
    sa.Enum(name="listing_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="price_unit").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="property_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="transaction_type").drop(op.get_bind(), checkfirst=True)
