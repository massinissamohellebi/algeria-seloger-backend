from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.mailer import Mailer, get_mailer
from app.reservations.service import ReservationService


def get_reservation_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> ReservationService:
    return ReservationService(session, mailer=mailer)
