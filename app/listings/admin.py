import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AdminUser
from app.core.database import get_db
from app.listings.dependencies import get_listing_service
from app.listings.models import ListingStatus
from app.listings.schemas import (
    AdminStatusUpdate,
    ListingPage,
    ListingRead,
)
from app.listings.service import ListingService

router = APIRouter(prefix="/admin/listings", tags=["admin"])

ServiceDep = Annotated[ListingService, Depends(get_listing_service)]
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=ListingPage)
async def admin_list_listings(
    _admin: AdminUser,
    service: ServiceDep,
    status: ListingStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ListingPage:
    return await service.list_all(status, page, size)


@router.post("/{listing_id}/status", response_model=ListingRead)
async def admin_set_status(
    listing_id: uuid.UUID,
    payload: AdminStatusUpdate,
    _admin: AdminUser,
    service: ServiceDep,
    session: SessionDep,
) -> ListingRead:
    listing = await service.set_status(listing_id, payload.status)
    await session.commit()
    return ListingRead.model_validate(listing)
