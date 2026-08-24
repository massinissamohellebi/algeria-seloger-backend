import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.reservations.dependencies import get_reservation_service
from app.reservations.schemas import (
    ReservationCreate,
    ReservationList,
    ReservationRead,
)
from app.reservations.service import ReservationService

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[ReservationService, Depends(get_reservation_service)]

router = APIRouter(tags=["reservations"])


@router.post(
    "/listings/{listing_id}/reservations",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation(
    listing_id: uuid.UUID,
    payload: ReservationCreate,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> ReservationRead:
    reservation = await service.create_reservation(current_user, listing_id, payload)
    await session.commit()
    return reservation


@router.get("/reservations/host", response_model=ReservationList)
async def list_host_reservations(
    current_user: CurrentUser,
    service: ServiceDep,
) -> ReservationList:
    return await service.list_for_host(current_user)


@router.get("/reservations/guest", response_model=ReservationList)
async def list_guest_reservations(
    current_user: CurrentUser,
    service: ServiceDep,
) -> ReservationList:
    return await service.list_for_guest(current_user)


@router.post("/reservations/{reservation_id}/confirm", response_model=ReservationRead)
async def confirm_reservation(
    reservation_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> ReservationRead:
    reservation = await service.confirm(reservation_id, current_user)
    await session.commit()
    return reservation


@router.post("/reservations/{reservation_id}/cancel", response_model=ReservationRead)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> ReservationRead:
    reservation = await service.cancel(reservation_id, current_user)
    await session.commit()
    return reservation
