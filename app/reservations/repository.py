import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.reservations.models import Reservation, ReservationStatus


class ReservationRepository:
    """Data-access for reservations (epic vacances)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        listing_id: uuid.UUID,
        guest_id: uuid.UUID,
        host_id: uuid.UUID,
        check_in: date,
        check_out: date,
        guests: int,
    ) -> Reservation:
        reservation = Reservation(
            listing_id=listing_id,
            guest_id=guest_id,
            host_id=host_id,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            status=ReservationStatus.pending,
        )
        self.session.add(reservation)
        await self.session.flush()
        await self.session.refresh(reservation)
        return reservation

    async def get_by_id(self, reservation_id: uuid.UUID) -> Reservation | None:
        return await self.session.get(Reservation, reservation_id)

    async def list_for_host(self, host_id: uuid.UUID) -> list[tuple[Reservation, str | None]]:
        return await self._list_with_guest(Reservation.host_id == host_id)

    async def list_for_guest(self, guest_id: uuid.UUID) -> list[tuple[Reservation, str | None]]:
        return await self._list_with_guest(Reservation.guest_id == guest_id)

    async def _list_with_guest(self, where_clause) -> list[tuple[Reservation, str | None]]:
        result = await self.session.execute(
            select(Reservation, User.full_name)
            .join(User, User.id == Reservation.guest_id)
            .where(where_clause)
            .order_by(Reservation.created_at.desc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def guest_name(self, guest_id: uuid.UUID) -> str | None:
        result = await self.session.execute(select(User.full_name).where(User.id == guest_id))
        return result.scalar_one_or_none()

    async def overlapping_pending(
        self,
        listing_id: uuid.UUID,
        check_in: date,
        check_out: date,
        exclude_id: uuid.UUID,
    ) -> list[Reservation]:
        """Other pending requests on the same listing whose dates overlap."""
        result = await self.session.execute(
            select(Reservation).where(
                Reservation.listing_id == listing_id,
                Reservation.id != exclude_id,
                Reservation.status == ReservationStatus.pending,
                Reservation.check_in < check_out,
                Reservation.check_out > check_in,
            )
        )
        return list(result.scalars())
