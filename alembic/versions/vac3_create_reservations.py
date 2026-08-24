"""epic vacances: reservations table

Revision ID: vac3_reservations
Revises: vac2_reviews
Create Date: 2026-08-22 16:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "vac3_reservations"
down_revision: str | None = "vac2_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

reservation_status = sa.Enum(
    "pending", "confirmed", "cancelled", name="reservation_status"
)


def upgrade() -> None:
    op.create_table(
        "reservations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID(), nullable=False),
        sa.Column("guest_id", sa.UUID(), nullable=False),
        sa.Column("host_id", sa.UUID(), nullable=False),
        sa.Column("check_in", sa.Date(), nullable=False),
        sa.Column("check_out", sa.Date(), nullable=False),
        sa.Column("guests", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            reservation_status,
            server_default="pending",
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["guest_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["host_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reservations_listing_id", "reservations", ["listing_id"])
    op.create_index("ix_reservations_guest_id", "reservations", ["guest_id"])
    op.create_index("ix_reservations_host_id", "reservations", ["host_id"])
    op.create_index("ix_reservations_status", "reservations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_reservations_status", table_name="reservations")
    op.drop_index("ix_reservations_host_id", table_name="reservations")
    op.drop_index("ix_reservations_guest_id", table_name="reservations")
    op.drop_index("ix_reservations_listing_id", table_name="reservations")
    op.drop_table("reservations")
    reservation_status.drop(op.get_bind(), checkfirst=True)
