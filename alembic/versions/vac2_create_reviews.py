"""epic vacances: reviews table

Revision ID: vac2_reviews
Revises: vac1_fields
Create Date: 2026-08-22 16:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "vac2_reviews"
down_revision: str | None = "vac1_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", "author_id", name="uq_review_listing_author"),
    )
    op.create_index("ix_reviews_listing_id", "reviews", ["listing_id"])
    op.create_index("ix_reviews_author_id", "reviews", ["author_id"])


def downgrade() -> None:
    op.drop_index("ix_reviews_author_id", table_name="reviews")
    op.drop_index("ix_reviews_listing_id", table_name="reviews")
    op.drop_table("reviews")
