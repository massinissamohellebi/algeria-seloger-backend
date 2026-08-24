import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.mailer import (
    ConsoleMailer,
    Mailer,
    build_reservation_cancelled_email,
    build_reservation_confirmed_email,
)
from app.listings.exceptions import ListingNotFoundError
from app.listings.models import Listing, ListingPhoto, TransactionType
from app.notifications.models import NotificationType
from app.notifications.repository import NotificationRepository
from app.reservations.exceptions import (
    InvalidDateRangeError,
    NotReservationHostError,
    NotVacationListingError,
    ReservationNotActionableError,
    ReservationNotFoundError,
    SelfReservationForbiddenError,
    TooManyGuestsError,
)
from app.reservations.models import Reservation, ReservationStatus
from app.reservations.repository import ReservationRepository
from app.reservations.schemas import (
    ListingPreview,
    ReservationCreate,
    ReservationList,
    ReservationRead,
)


class ReservationService:
    def __init__(self, session: AsyncSession, mailer: Mailer | None = None) -> None:
        self.session = session
        self.repo = ReservationRepository(session)
        self.notifications = NotificationRepository(session)
        self.mailer = mailer or ConsoleMailer()

    # --- Create ------------------------------------------------------------

    async def create_reservation(
        self, guest: User, listing_id: uuid.UUID, data: ReservationCreate
    ) -> ReservationRead:
        listing = await self.session.get(Listing, listing_id)
        if listing is None:
            raise ListingNotFoundError()
        if listing.transaction_type != TransactionType.vacances:
            raise NotVacationListingError()
        if listing.owner_id == guest.id:
            raise SelfReservationForbiddenError()
        if data.check_out <= data.check_in:
            raise InvalidDateRangeError()
        if listing.max_guests is not None and data.guests > listing.max_guests:
            raise TooManyGuestsError()

        reservation = await self.repo.create(
            listing_id=listing.id,
            guest_id=guest.id,
            host_id=listing.owner_id,
            check_in=data.check_in,
            check_out=data.check_out,
            guests=data.guests,
        )

        guest_label = guest.full_name or "Un voyageur"
        await self.notifications.create(
            user_id=listing.owner_id,
            type=NotificationType.reservation_request,
            title="Nouvelle demande de réservation",
            body=(
                f"{guest_label} souhaite réserver « {listing.title} » "
                f"du {data.check_in} au {data.check_out}."
            ),
            link="/profil/reservations",
        )

        cover = await self._cover_url(listing.id)
        return self._to_read(reservation, guest.full_name, listing, cover)

    # --- Lists -------------------------------------------------------------

    async def list_for_host(self, host: User) -> ReservationList:
        rows = await self.repo.list_for_host(host.id)
        return await self._rows_to_list(rows)

    async def list_for_guest(self, guest: User) -> ReservationList:
        rows = await self.repo.list_for_guest(guest.id)
        return await self._rows_to_list(rows)

    # --- Host actions ------------------------------------------------------

    async def confirm(self, reservation_id: uuid.UUID, host: User) -> ReservationRead:
        reservation = await self._get_host_reservation(reservation_id, host)
        if reservation.status != ReservationStatus.pending:
            raise ReservationNotActionableError()

        reservation.status = ReservationStatus.confirmed
        listing = await self.session.get(Listing, reservation.listing_id)
        title = listing.title if listing else "votre logement"

        # Auto-cancel the other overlapping pending requests.
        others = await self.repo.overlapping_pending(
            reservation.listing_id,
            reservation.check_in,
            reservation.check_out,
            reservation.id,
        )
        for other in others:
            other.status = ReservationStatus.cancelled
            await self._notify_cancellation(other, title)

        await self.session.flush()

        # Confirmation email + notification for the retained guest.
        guest = await self.session.get(User, reservation.guest_id)
        if guest is not None:
            subject, body = build_reservation_confirmed_email(
                title,
                str(reservation.check_in),
                str(reservation.check_out),
                reservation.guests,
            )
            await self.mailer.send(to=guest.email, subject=subject, body=body)
        await self.notifications.create(
            user_id=reservation.guest_id,
            type=NotificationType.reservation_confirmed,
            title="Réservation confirmée",
            body=f"Votre réservation pour « {title} » a été confirmée.",
            link="/profil/reservations",
        )

        cover = await self._cover_url(reservation.listing_id)
        guest_name = await self.repo.guest_name(reservation.guest_id)
        return self._to_read(reservation, guest_name, listing, cover)

    async def cancel(self, reservation_id: uuid.UUID, user: User) -> ReservationRead:
        reservation = await self.repo.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError()
        if user.id not in (reservation.host_id, reservation.guest_id):
            raise NotReservationHostError()
        if reservation.status == ReservationStatus.cancelled:
            raise ReservationNotActionableError()

        reservation.status = ReservationStatus.cancelled
        listing = await self.session.get(Listing, reservation.listing_id)
        title = listing.title if listing else "votre logement"
        await self.session.flush()

        # Notify the guest when the host is the one cancelling.
        if user.id == reservation.host_id:
            await self._notify_cancellation(reservation, title)

        cover = await self._cover_url(reservation.listing_id)
        guest_name = await self.repo.guest_name(reservation.guest_id)
        return self._to_read(reservation, guest_name, listing, cover)

    # --- Helpers -----------------------------------------------------------

    async def _get_host_reservation(self, reservation_id: uuid.UUID, host: User) -> Reservation:
        reservation = await self.repo.get_by_id(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError()
        if reservation.host_id != host.id:
            raise NotReservationHostError()
        return reservation

    async def _notify_cancellation(self, reservation: Reservation, listing_title: str) -> None:
        guest = await self.session.get(User, reservation.guest_id)
        if guest is not None:
            subject, body = build_reservation_cancelled_email(
                listing_title,
                str(reservation.check_in),
                str(reservation.check_out),
            )
            await self.mailer.send(to=guest.email, subject=subject, body=body)
        await self.notifications.create(
            user_id=reservation.guest_id,
            type=NotificationType.reservation_cancelled,
            title="Réservation annulée",
            body=f"Votre réservation pour « {listing_title} » a été annulée.",
            link="/profil/reservations",
        )

    async def _rows_to_list(self, rows: list[tuple[Reservation, str | None]]) -> ReservationList:
        listing_ids = list({res.listing_id for res, _ in rows})
        covers = await self._cover_urls(listing_ids)
        items = [
            self._to_read(res, name, res.listing, covers.get(res.listing_id)) for res, name in rows
        ]
        return ReservationList(items=items, total=len(items))

    def _to_read(
        self,
        reservation: Reservation,
        guest_name: str | None,
        listing: Listing | None,
        cover_url: str | None,
    ) -> ReservationRead:
        preview = None
        if listing is not None:
            preview = ListingPreview(id=listing.id, title=listing.title, cover_url=cover_url)
        return ReservationRead(
            id=reservation.id,
            listing_id=reservation.listing_id,
            listing=preview,
            guest_id=reservation.guest_id,
            guest_name=guest_name or "Un voyageur",
            host_id=reservation.host_id,
            check_in=reservation.check_in,
            check_out=reservation.check_out,
            guests=reservation.guests,
            status=reservation.status,
            created_at=reservation.created_at,
        )

    async def _cover_url(self, listing_id: uuid.UUID) -> str | None:
        return (await self._cover_urls([listing_id])).get(listing_id)

    async def _cover_urls(self, listing_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not listing_ids:
            return {}
        result = await self.session.execute(
            select(ListingPhoto.listing_id, ListingPhoto.url).where(
                ListingPhoto.listing_id.in_(listing_ids),
                ListingPhoto.is_cover.is_(True),
            )
        )
        return {row[0]: row[1] for row in result.all()}
