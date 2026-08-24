"""epic vacances: vacation-rental fields on listings

Revision ID: vac1_fields
Revises: f2a3b4c5d6e7
Create Date: 2026-08-22 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "vac1_fields"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("max_guests", sa.Integer(), nullable=True))
    op.add_column("listings", sa.Column("beds", sa.Integer(), nullable=True))
    op.add_column("listings", sa.Column("pets_allowed", sa.Boolean(), nullable=True))
    op.add_column("listings", sa.Column("checkin_from", sa.String(length=5), nullable=True))
    op.add_column("listings", sa.Column("checkin_to", sa.String(length=5), nullable=True))
    op.add_column("listings", sa.Column("checkout_before", sa.String(length=5), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "checkout_before")
    op.drop_column("listings", "checkin_to")
    op.drop_column("listings", "checkin_from")
    op.drop_column("listings", "pets_allowed")
    op.drop_column("listings", "beds")
    op.drop_column("listings", "max_guests")
