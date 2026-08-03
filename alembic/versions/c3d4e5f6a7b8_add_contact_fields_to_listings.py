"""add contact_name and contact_phone to listings

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-02 22:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("contact_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "listings",
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("listings", "contact_phone")
    op.drop_column("listings", "contact_name")
