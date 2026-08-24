import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    UUID,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.listings.models import Listing


class ReservationStatus(enum.StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


class Reservation(Base):
    """A guest's booking request on a vacation listing (epic vacances).

    Multiple guests may request the same dates; the host validates one, which
    confirms it and auto-cancels the other overlapping pending requests.
    """

    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    guest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    host_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    guests: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"),
        default=ReservationStatus.pending,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    listing: Mapped["Listing"] = relationship(lazy="selectin")

    __table_args__ = (
        Index("ix_reservations_listing_id", "listing_id"),
        Index("ix_reservations_guest_id", "guest_id"),
        Index("ix_reservations_host_id", "host_id"),
    )
