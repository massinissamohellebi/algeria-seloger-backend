import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.listings.models import (
    Listing,
    ListingPhoto,
    ListingStatus,
    PropertyType,
    TransactionType,
)
from app.listings.schemas import SortOption


@dataclass
class ListingFilters:
    transaction_type: TransactionType | None = None
    property_type: PropertyType | None = None
    wilaya: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    furnished: bool | None = None
    rooms: int | None = None


class ListingRepository:
    """Data-access layer for listings (no business logic)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, listing: Listing) -> Listing:
        self.session.add(listing)
        await self.session.flush()
        # Re-fetch to load server-side defaults and the photos relationship
        # without triggering a lazy load later in the (sync) serialization step.
        return await self.get_by_id(listing.id)  # type: ignore[return-value]

    async def get_by_id(self, listing_id: uuid.UUID) -> Listing | None:
        result = await self.session.execute(
            select(Listing).where(Listing.id == listing_id).options(selectinload(Listing.photos))
        )
        return result.scalar_one_or_none()

    async def update(self, listing: Listing, data: dict) -> Listing:
        for key, value in data.items():
            setattr(listing, key, value)
        await self.session.flush()
        # Re-fetch so onupdate/server columns and photos are loaded eagerly.
        return await self.get_by_id(listing.id)  # type: ignore[return-value]

    async def delete(self, listing: Listing) -> None:
        await self.session.delete(listing)
        await self.session.flush()

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Listing]:
        result = await self.session.execute(
            select(Listing)
            .where(Listing.owner_id == owner_id)
            .options(selectinload(Listing.photos))
            .order_by(Listing.created_at.desc())
        )
        return list(result.scalars().all())

    # --- photos ---------------------------------------------------------

    async def count_photos(self, listing_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ListingPhoto)
            .where(ListingPhoto.listing_id == listing_id)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def add_photo(
        self, *, listing_id: uuid.UUID, url: str, position: int, is_cover: bool
    ) -> ListingPhoto:
        photo = ListingPhoto(listing_id=listing_id, url=url, position=position, is_cover=is_cover)
        self.session.add(photo)
        await self.session.flush()
        await self.session.refresh(photo)
        return photo

    async def get_photo(self, listing_id: uuid.UUID, photo_id: uuid.UUID) -> ListingPhoto | None:
        stmt = select(ListingPhoto).where(
            ListingPhoto.id == photo_id,
            ListingPhoto.listing_id == listing_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_photos(self, listing_id: uuid.UUID) -> list[ListingPhoto]:
        stmt = (
            select(ListingPhoto)
            .where(ListingPhoto.listing_id == listing_id)
            .order_by(ListingPhoto.position)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_photo(self, photo: ListingPhoto) -> None:
        await self.session.delete(photo)
        await self.session.flush()

    async def resequence_photos(self, listing_id: uuid.UUID) -> None:
        """Re-number remaining photos 0..n and keep the first one as cover."""
        photos = await self.list_photos(listing_id)
        for index, photo in enumerate(photos):
            photo.position = index
            photo.is_cover = index == 0
        await self.session.flush()

    # --- filtering ------------------------------------------------------

    def _apply_filters(self, stmt, filters: ListingFilters):
        stmt = stmt.where(Listing.status == ListingStatus.published)
        if filters.transaction_type is not None:
            stmt = stmt.where(Listing.transaction_type == filters.transaction_type)
        if filters.property_type is not None:
            stmt = stmt.where(Listing.property_type == filters.property_type)
        if filters.wilaya:
            stmt = stmt.where(Listing.wilaya == filters.wilaya)
        if filters.price_min is not None:
            stmt = stmt.where(Listing.price >= filters.price_min)
        if filters.price_max is not None:
            stmt = stmt.where(Listing.price <= filters.price_max)
        if filters.furnished is not None:
            stmt = stmt.where(Listing.furnished == filters.furnished)
        if filters.rooms is not None:
            stmt = stmt.where(Listing.rooms >= filters.rooms)
        return stmt

    @staticmethod
    def _apply_sort(stmt, sort: SortOption):
        match sort:
            case SortOption.price_asc:
                return stmt.order_by(Listing.price.asc(), Listing.created_at.desc())
            case SortOption.price_desc:
                return stmt.order_by(Listing.price.desc(), Listing.created_at.desc())
            case SortOption.surface_asc:
                return stmt.order_by(Listing.surface.asc(), Listing.created_at.desc())
            case SortOption.surface_desc:
                return stmt.order_by(Listing.surface.desc(), Listing.created_at.desc())
            case _:  # newest
                return stmt.order_by(Listing.published_at.desc(), Listing.created_at.desc())

    async def list_published(
        self,
        filters: ListingFilters,
        sort: SortOption,
        page: int,
        size: int,
    ) -> tuple[list[Listing], int]:
        base = self._apply_filters(select(Listing), filters)

        count_stmt = self._apply_filters(select(func.count()).select_from(Listing), filters)
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = self._apply_sort(base, sort).options(selectinload(Listing.photos))
        stmt = stmt.offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
