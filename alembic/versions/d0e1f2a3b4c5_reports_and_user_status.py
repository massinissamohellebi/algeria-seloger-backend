"""epic 10: reports table + user moderation status

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-21 10:00:00.000000

Adds the reports table (listing XOR user target) and the user moderation
fields (status, suspended_until).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("suspended_until", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum(
                "spam",
                "fraud",
                "harassment",
                "adult",
                "inappropriate",
                name="report_reason",
            ),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("open", "resolved", "dismissed", name="report_status"),
            server_default="open",
            nullable=False,
        ),
        sa.Column("reporter_id", sa.UUID(), nullable=True),
        sa.Column("listing_id", sa.UUID(), nullable=True),
        sa.Column("reported_user_id", sa.UUID(), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["reported_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(listing_id IS NULL) != (reported_user_id IS NULL)",
            name="ck_reports_single_target",
        ),
    )
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_table("reports")
    sa.Enum(name="report_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="report_reason").drop(op.get_bind(), checkfirst=True)

    op.drop_column("users", "suspended_until")
    op.drop_column("users", "status")
