import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.favorites.dependencies import get_favorite_service
from app.favorites.schemas import FavoriteState
from app.favorites.service import FavoriteService
from app.listings.schemas import ListingPage

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[FavoriteService, Depends(get_favorite_service)]

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=ListingPage)
async def list_favorites(
    current_user: CurrentUser,
    service: ServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ListingPage:
    return await service.list(current_user, page, size)


@router.post("/{listing_id}", response_model=FavoriteState)
async def add_favorite(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> FavoriteState:
    await service.add(current_user, listing_id)
    await session.commit()
    return FavoriteState(listing_id=listing_id, is_favorited=True)


@router.delete("/{listing_id}", response_model=FavoriteState)
async def remove_favorite(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> FavoriteState:
    await service.remove(current_user, listing_id)
    await session.commit()
    return FavoriteState(listing_id=listing_id, is_favorited=False)
