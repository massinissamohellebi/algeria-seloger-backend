"""reference tables (statuses/reasons) + user.wilaya FK

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-22 10:00:00.000000

Turns the status/reason free/enum values into seeded reference tables with FK
relations, and makes `users.wilaya` a FK to the wilayas table (code-keyed,
mirroring the Wilaya model).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_STATUS_SEED = [("active", "Actif"), ("suspended", "Suspendu"), ("banned", "Banni")]
REPORT_STATUS_SEED = [("open", "Ouvert"), ("resolved", "Résolu"), ("dismissed", "Rejeté")]
REPORT_REASON_SEED = [
    ("spam", "Spam"),
    ("fraud", "Arnaque / fraude"),
    ("harassment", "Harcèlement"),
    ("adult", "Contenu adulte"),
    ("inappropriate", "Inapproprié"),
]


def _seed(table_name: str, code_len: int, label_len: int, rows: list[tuple[str, str]]) -> None:
    tbl = sa.table(
        table_name,
        sa.column("code", sa.String(code_len)),
        sa.column("label", sa.String(label_len)),
    )
    op.bulk_insert(tbl, [{"code": c, "label": lbl} for c, lbl in rows])


def upgrade() -> None:
    # 1. Reference tables (code-keyed like wilayas) + seed.
    op.create_table(
        "user_statuses",
        sa.Column("code", sa.String(20), primary_key=True),
        sa.Column("label", sa.String(50), nullable=False),
    )
    op.create_table(
        "report_statuses",
        sa.Column("code", sa.String(20), primary_key=True),
        sa.Column("label", sa.String(50), nullable=False),
    )
    op.create_table(
        "report_reasons",
        sa.Column("code", sa.String(30), primary_key=True),
        sa.Column("label", sa.String(80), nullable=False),
    )
    _seed("user_statuses", 20, 50, USER_STATUS_SEED)
    _seed("report_statuses", 20, 50, REPORT_STATUS_SEED)
    _seed("report_reasons", 30, 80, REPORT_REASON_SEED)

    # 2. users.status → FK to user_statuses.
    op.create_foreign_key(
        "fk_users_status", "users", "user_statuses", ["status"], ["code"]
    )

    # 3. reports.reason / status : enum → varchar + FK, then drop enum types.
    op.alter_column(
        "reports",
        "reason",
        type_=sa.String(30),
        existing_nullable=False,
        postgresql_using="reason::text",
    )
    op.alter_column(
        "reports",
        "status",
        type_=sa.String(20),
        existing_nullable=False,
        server_default=sa.text("'open'"),
        postgresql_using="status::text",
    )
    op.create_foreign_key(
        "fk_reports_reason", "reports", "report_reasons", ["reason"], ["code"]
    )
    op.create_foreign_key(
        "fk_reports_status", "reports", "report_statuses", ["status"], ["code"]
    )
    sa.Enum(name="report_reason").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="report_status").drop(op.get_bind(), checkfirst=True)

    # 4. users.wilaya (name) → wilaya_code FK, backfilled by matching name_fr.
    op.add_column("users", sa.Column("wilaya_code", sa.CHAR(2), nullable=True))
    op.execute(
        "UPDATE users SET wilaya_code = w.code FROM wilayas w "
        "WHERE users.wilaya = w.name_fr"
    )
    op.create_foreign_key(
        "fk_users_wilaya", "users", "wilayas", ["wilaya_code"], ["code"]
    )
    op.drop_column("users", "wilaya")


def downgrade() -> None:
    # 4. wilaya_code → wilaya name.
    op.add_column("users", sa.Column("wilaya", sa.String(100), nullable=True))
    op.execute(
        "UPDATE users SET wilaya = w.name_fr FROM wilayas w "
        "WHERE users.wilaya_code = w.code"
    )
    op.drop_constraint("fk_users_wilaya", "users", type_="foreignkey")
    op.drop_column("users", "wilaya_code")

    # 3. reports varchar → enum.
    reason_enum = sa.Enum(
        "spam", "fraud", "harassment", "adult", "inappropriate", name="report_reason"
    )
    status_enum = sa.Enum("open", "resolved", "dismissed", name="report_status")
    reason_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)
    op.drop_constraint("fk_reports_reason", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_status", "reports", type_="foreignkey")
    op.alter_column(
        "reports",
        "reason",
        type_=reason_enum,
        existing_nullable=False,
        postgresql_using="reason::report_reason",
    )
    # Drop the text default before retyping (it can't cast to the enum), then
    # restore it as an enum-typed default.
    op.alter_column("reports", "status", server_default=None)
    op.alter_column(
        "reports",
        "status",
        type_=status_enum,
        existing_nullable=False,
        postgresql_using="status::report_status",
    )
    op.alter_column(
        "reports", "status", server_default=sa.text("'open'::report_status")
    )

    # 2 + 1. Drop the user.status FK and the reference tables.
    op.drop_constraint("fk_users_status", "users", type_="foreignkey")
    op.drop_table("report_reasons")
    op.drop_table("report_statuses")
    op.drop_table("user_statuses")
