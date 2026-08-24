import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    UUID,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.reference.models import ReportReasonRef, ReportStatusRef


class ReportReason(enum.StrEnum):
    spam = "spam"
    fraud = "fraud"
    harassment = "harassment"
    adult = "adult"
    inappropriate = "inappropriate"


class ReportStatus(enum.StrEnum):
    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


class Report(Base):
    """A user/anonymous report against a listing XOR a user (epic 10).

    Exactly one of `listing_id` / `reported_user_id` is set (DB check
    constraint). `reporter_id` is null for anonymous reports.
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reason: Mapped[str] = mapped_column(
        String(30), ForeignKey("report_reasons.code"), nullable=False
    )
    reason_ref: Mapped["ReportReasonRef"] = relationship(lazy="selectin")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("report_statuses.code"),
        default="open",
        server_default="open",
        nullable=False,
    )
    status_ref: Mapped["ReportStatusRef"] = relationship(
        "ReportStatusRef", lazy="selectin"
    )
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=True,
    )
    reported_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # Exactly one target: listing XOR user.
        CheckConstraint(
            "(listing_id IS NULL) != (reported_user_id IS NULL)",
            name="ck_reports_single_target",
        ),
        Index("ix_reports_status", "status"),
        Index("ix_reports_created_at", "created_at"),
    )
