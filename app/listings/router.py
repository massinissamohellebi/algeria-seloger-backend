import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, OptionalCurrentUser
from app.auth.models import User
from app.core.database import get_db
from app.favorites.dependencies import get_favorite_repository
from app.favorites.repository import FavoriteRepository
from app.listings.dependencies import get_listing_service, get_photo_service
from app.listings.models import PropertyType, TransactionType
from app.listings.repository import ListingFilters
from app.listings.schemas import (
    ListingCreate,
    ListingPage,
    ListingRead,
    ListingSummary,
    ListingUpdate,
    PhotoRead,
    SortOption,
)
from app.listings.service import ListingService, PhotoService
from app.reviews.dependencies import get_review_service
from app.reviews.service import ReviewService

router = APIRouter(prefix="/listings", tags=["listings"])

ServiceDep = Annotated[ListingService, Depends(get_listing_service)]
PhotoServiceDep = Annotated[PhotoService, Depends(get_photo_service)]
SessionDep = Annotated[AsyncSession, Depends(get_db)]
FavRepoDep = Annotated[FavoriteRepository, Depends(get_favorite_repository)]
ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]


async def _mark_favorites(
    items: list[ListingSummary],
    user: User | None,
    favorites: FavoriteRepository,
) -> None:
    """Batch-resolve `is_favorited` for the authed caller (no N+1)."""
    if user is None or not items:
        return
    favorited = await favorites.favorited_ids(user.id, [item.id for item in items])
    for item in items:
        item.is_favorited = item.id in favorited


@router.get("", response_model=ListingPage)
async def list_listings(
    service: ServiceDep,
    current_user: OptionalCurrentUser,
    favorites: FavRepoDep,
    q: Annotated[str | None, Query(max_length=200)] = None,
    transaction_type: TransactionType | None = None,
    property_type: Annotated[list[PropertyType] | None, Query()] = None,
    wilaya: str | None = None,
    city: Annotated[str | None, Query(max_length=100)] = None,
    price_min: Annotated[int | None, Query(ge=0)] = None,
    price_max: Annotated[int | None, Query(ge=0)] = None,
    surface_min: Annotated[int | None, Query(ge=0)] = None,
    surface_max: Annotated[int | None, Query(ge=0)] = None,
    furnished: bool | None = None,
    rooms_min: Annotated[int | None, Query(ge=0)] = None,
    amenities: Annotated[list[str] | None, Query()] = None,
    sort: SortOption = SortOption.newest,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ListingPage:
    filters = ListingFilters(
        transaction_type=transaction_type,
        property_type=property_type,
        wilaya=wilaya,
        city=city,
        price_min=price_min,
        price_max=price_max,
        surface_min=surface_min,
        surface_max=surface_max,
        furnished=furnished,
        rooms_min=rooms_min,
        amenities=[a for a in amenities if a.strip()] if amenities else None,
        q=q.strip() if q and q.strip() else None,
    )
    result = await service.list_published(filters, sort, page, size)
    await _mark_favorites(result.items, current_user, favorites)
    return result


@router.get("/mine", response_model=list[ListingSummary])
async def list_my_listings(
    current_user: CurrentUser,
    service: ServiceDep,
) -> list[ListingSummary]:
    return await service.list_mine(current_user)


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
async def create_listing(
    payload: ListingCreate,
    current_user: CurrentUser,
    service: ServiceDep,
    session: SessionDep,
) -> ListingRead:
    listing = await service.create_listing(current_user, payload)
    await session.commit()
    return ListingRead.model_validate(listing)


@router.get("/{listing_id}", response_model=ListingRead)
async def get_listing(
    listing_id: uuid.UUID,
    current_user: OptionalCurrentUser,
    service: ServiceDep,
    favorites: FavRepoDep,
    reviews: ReviewServiceDep,
) -> ListingRead:
    listing = await service.get_listing(listing_id, current_user)
    read = ListingRead.model_validate(listing)
    if current_user is not None:
        read.is_favorited = await favorites.exists(current_user.id, listing.id)
    average, count = await reviews.aggregate(listing.id)
    read.rating_avg = round(average, 2) if average is not None else None
    read.review_count = count
    return read


@router.patch("/{listing_id}", response_model=ListingRead)
async def update_listing(
    listing_id: uuid.UUID,
    payload: ListingUpdate,
    current_user: CurrentUser,
    service: ServiceDep,
    session: SessionDep,
) -> ListingRead:
    listing = await service.update_listing(listing_id, current_user, payload)
    await session.commit()
    return ListingRead.model_validate(listing)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_listing(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    service: ServiceDep,
    session: SessionDep,
) -> None:
    await service.delete_listing(listing_id, current_user)
    await session.commit()


@router.post("/{listing_id}/publish", response_model=ListingRead)
async def publish_listing(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    service: ServiceDep,
    session: SessionDep,
) -> ListingRead:
    listing = await service.publish_listing(listing_id, current_user)
    await session.commit()
    return ListingRead.model_validate(listing)


@router.post(
    "/{listing_id}/photos",
    response_model=PhotoRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photo(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    service: PhotoServiceDep,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
) -> PhotoRead:
    data = await file.read()
    photo = await service.add_photo(
        listing_id, current_user, data=data, content_type=file.content_type
    )
    await session.commit()
    return PhotoRead.model_validate(photo)


@router.delete(
    "/{listing_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_photo(
    listing_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: CurrentUser,
    service: PhotoServiceDep,
    session: SessionDep,
) -> None:
    await service.delete_photo(listing_id, current_user, photo_id)
    await session.commit()
