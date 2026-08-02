import math
import uuid
from datetime import UTC, datetime

from app.auth.models import User
from app.listings.exceptions import (
    InvalidStatusTransitionError,
    ListingNotFoundError,
    NotListingOwnerError,
)
from app.listings.models import Listing, ListingPhoto, ListingStatus
from app.listings.repository import ListingFilters, ListingRepository
from app.listings.schemas import (
    ListingCreate,
    ListingPage,
    ListingSummary,
    ListingUpdate,
    SortOption,
)


def _cover_url(photos: list[ListingPhoto]) -> str | None:
    if not photos:
        return None
    cover = next((p for p in photos if p.is_cover), photos[0])
    return cover.url


def _to_summary(listing: Listing) -> ListingSummary:
    summary = ListingSummary.model_validate(listing)
    summary.cover_url = _cover_url(listing.photos)
    return summary


class ListingService:
    """Business logic for listings CRUD, visibility and status lifecycle."""

    def __init__(self, repository: ListingRepository) -> None:
        self.repository = repository

    async def create_listing(self, owner: User, payload: ListingCreate) -> Listing:
        listing = Listing(owner_id=owner.id, status=ListingStatus.draft)
        for key, value in payload.model_dump().items():
            setattr(listing, key, value)
        return await self.repository.create(listing)

    async def get_listing(self, listing_id: uuid.UUID, current_user: User | None) -> Listing:
        listing = await self.repository.get_by_id(listing_id)
        if listing is None:
            raise ListingNotFoundError()
        if listing.status == ListingStatus.published:
            return listing
        if current_user is not None and listing.owner_id == current_user.id:
            return listing
        # Hide existence of non-published listings from non-owners.
        raise ListingNotFoundError()

    async def _get_owned(self, listing_id: uuid.UUID, owner: User) -> Listing:
        listing = await self.repository.get_by_id(listing_id)
        if listing is None:
            raise ListingNotFoundError()
        if listing.owner_id != owner.id:
            raise NotListingOwnerError()
        return listing

    async def update_listing(
        self, listing_id: uuid.UUID, owner: User, payload: ListingUpdate
    ) -> Listing:
        listing = await self._get_owned(listing_id, owner)
        data = payload.model_dump(exclude_unset=True)
        return await self.repository.update(listing, data)

    async def delete_listing(self, listing_id: uuid.UUID, owner: User) -> None:
        listing = await self._get_owned(listing_id, owner)
        await self.repository.delete(listing)

    async def publish_listing(self, listing_id: uuid.UUID, owner: User) -> Listing:
        listing = await self._get_owned(listing_id, owner)
        if listing.status != ListingStatus.draft:
            raise InvalidStatusTransitionError(
                f"Cannot publish a listing with status '{listing.status}'."
            )
        listing.status = ListingStatus.published
        listing.published_at = datetime.now(UTC)
        return await self.repository.update(listing, {})

    async def list_published(
        self,
        filters: ListingFilters,
        sort: SortOption,
        page: int,
        size: int,
    ) -> ListingPage:
        listings, total = await self.repository.list_published(filters, sort, page, size)
        return ListingPage(
            items=[_to_summary(item) for item in listings],
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if size else 0,
        )

    async def list_mine(self, owner: User) -> list[ListingSummary]:
        listings = await self.repository.list_by_owner(owner.id)
        return [_to_summary(item) for item in listings]
