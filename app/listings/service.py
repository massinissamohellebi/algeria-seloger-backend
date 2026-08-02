import math
import uuid
from datetime import UTC, datetime

from app.auth.models import User
from app.core.config import settings
from app.core.storage import StorageBackend, build_object_key
from app.listings.exceptions import (
    InvalidPhotoError,
    InvalidStatusTransitionError,
    ListingNotFoundError,
    MaxPhotosReachedError,
    NotListingOwnerError,
    PhotoNotFoundError,
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


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class PhotoService:
    """Upload/delete listing photos with server-side validation and ownership."""

    def __init__(self, repository: ListingRepository, storage: StorageBackend) -> None:
        self.repository = repository
        self.storage = storage

    async def _get_owned(self, listing_id: uuid.UUID, owner: User) -> Listing:
        listing = await self.repository.get_by_id(listing_id)
        if listing is None:
            raise ListingNotFoundError()
        if listing.owner_id != owner.id:
            raise NotListingOwnerError()
        return listing

    async def add_photo(
        self,
        listing_id: uuid.UUID,
        owner: User,
        *,
        data: bytes,
        content_type: str | None,
    ) -> ListingPhoto:
        await self._get_owned(listing_id, owner)

        count = await self.repository.count_photos(listing_id)
        if count >= settings.max_photos_per_listing:
            raise MaxPhotosReachedError()
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise InvalidPhotoError("Only JPEG, PNG or WebP images are accepted.")
        if not data:
            raise InvalidPhotoError("The uploaded file is empty.")
        if len(data) > settings.max_photo_size_bytes:
            raise InvalidPhotoError("The image exceeds the maximum allowed size.")

        key = build_object_key(listing_id, content_type)
        url = await self.storage.upload(key, data, content_type)
        return await self.repository.add_photo(
            listing_id=listing_id,
            url=url,
            position=count,
            is_cover=count == 0,
        )

    async def delete_photo(self, listing_id: uuid.UUID, owner: User, photo_id: uuid.UUID) -> None:
        await self._get_owned(listing_id, owner)
        photo = await self.repository.get_photo(listing_id, photo_id)
        if photo is None:
            raise PhotoNotFoundError()
        await self.storage.delete(photo.url)
        await self.repository.delete_photo(photo)
        await self.repository.resequence_photos(listing_id)
