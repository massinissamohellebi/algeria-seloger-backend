"""Reference (lookup) tables for statuses & reasons.

Each is a small, seeded table keyed by a natural `code` (mirroring the Wilaya
model, which is also code-keyed). The domain columns on `users` / `reports`
hold the code and carry a foreign key to these tables, so the values are
DB-backed models with real relations rather than free strings.

The matching `StrEnum`s (in auth/reports models) stay the API-level source of
valid codes; these tables add referential integrity + human labels.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserStatusRef(Base):
    __tablename__ = "user_statuses"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False)


class ReportStatusRef(Base):
    __tablename__ = "report_statuses"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False)


class ReportReasonRef(Base):
    __tablename__ = "report_reasons"

    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)


# --- Seed data (code, label) — labels are canonical French ------------------

USER_STATUS_SEED: list[tuple[str, str]] = [
    ("active", "Actif"),
    ("suspended", "Suspendu"),
    ("banned", "Banni"),
]

REPORT_STATUS_SEED: list[tuple[str, str]] = [
    ("open", "Ouvert"),
    ("resolved", "Résolu"),
    ("dismissed", "Rejeté"),
]

REPORT_REASON_SEED: list[tuple[str, str]] = [
    ("spam", "Spam"),
    ("fraud", "Arnaque / fraude"),
    ("harassment", "Harcèlement"),
    ("adult", "Contenu adulte"),
    ("inappropriate", "Inapproprié"),
]
