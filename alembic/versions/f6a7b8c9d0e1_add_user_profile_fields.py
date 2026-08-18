"""add user profile fields (phone, wilaya, bio, account_type)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-05 10:00:00.000000

Adds editable profile fields to the users table for the profile screen.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("wilaya", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "account_type",
            sa.String(length=20),
            nullable=False,
            server_default="particulier",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "account_type")
    op.drop_column("users", "bio")
    op.drop_column("users", "wilaya")
    op.drop_column("users", "phone")
