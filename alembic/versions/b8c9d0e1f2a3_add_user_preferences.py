"""epic 9: user preferences (language, email_notifications)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-19 09:00:00.000000

Adds the profile preference columns with safe defaults so existing rows
backfill to French + notifications enabled.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "language",
            sa.String(length=2),
            server_default="fr",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_notifications",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "email_notifications")
    op.drop_column("users", "language")
