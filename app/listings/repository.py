import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

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
    property_type: list[PropertyType] | None = None
    wilaya: str | None = None
    city: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    surface_min: int | None = None
    surface_max: int | None = None
    furnished: bool | None = None
    rooms_min: int | None = None
    amenities: list[str] | None = None
    q: str | None = None


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

    @property
    def _dialect(self) -> str:
        """Dialect name of the bound engine (e.g. 'postgresql', 'sqlite')."""
        return self.session.bind.dialect.name

    def _fulltext_clause(self, q: str) -> ColumnElement[bool]:
        """Build a parameterised full-text WHERE clause for the given query.

        On PostgreSQL this uses the migration-managed ``search_vector`` tsvector
        column with ``websearch_to_tsquery('french', :q)``. On any other dialect
        (SQLite in the test suite) it falls back to a parameterised ``LIKE`` over
        ``title || ' ' || description``. Both bind ``q`` as a parameter — never
        interpolated into SQL — so malicious input cannot inject.
        """
        if self._dialect == "postgresql":
            return text("search_vector @@ websearch_to_tsquery('french', :q)").bindparams(q=q)
        pattern = f"%{q.lower()}%"
        return text("lower(title || ' ' || coalesce(description, '')) LIKE :pattern").bindparams(
            pattern=pattern
        )

    def _amenity_clause(self, amenity: str, index: int) -> ColumnElement[bool]:
        """Parameterised "listing contains this amenity" clause (dialect-aware).

        ``Listing.amenities`` is a JSON array of strings. On PostgreSQL we query
        the jsonb array-contains operator ``@>``; on any other dialect (SQLite in
        the test suite) we scan the JSON array with ``json_each``. Each amenity
        value is bound as a parameter (unique name per index) — never interpolated
        — so it cannot inject. Callers AND several of these together to require
        every requested amenity.
        """
        param = f"am_{index}"
        if self._dialect == "postgresql":
            return text(f"amenities::jsonb @> jsonb_build_array(:{param})").bindparams(
                **{param: amenity}
            )
        return text(
            f"EXISTS (SELECT 1 FROM json_each(listings.amenities) WHERE value = :{param})"
        ).bindparams(**{param: amenity})

    def _apply_filters(self, stmt, filters: ListingFilters):
        stmt = stmt.where(Listing.status == ListingStatus.published)
        if filters.transaction_type is not None:
            stmt = stmt.where(Listing.transaction_type == filters.transaction_type)
        if filters.property_type:
            stmt = stmt.where(Listing.property_type.in_(filters.property_type))
        if filters.wilaya:
            stmt = stmt.where(Listing.wilaya == filters.wilaya)
        if filters.city:
            stmt = stmt.where(Listing.city == filters.city)
        if filters.price_min is not None:
            stmt = stmt.where(Listing.price >= filters.price_min)
        if filters.price_max is not None:
            stmt = stmt.where(Listing.price <= filters.price_max)
        if filters.surface_min is not None:
            stmt = stmt.where(Listing.surface >= filters.surface_min)
        if filters.surface_max is not None:
            stmt = stmt.where(Listing.surface <= filters.surface_max)
        if filters.furnished is not None:
            stmt = stmt.where(Listing.furnished == filters.furnished)
        if filters.rooms_min is not None:
            stmt = stmt.where(Listing.rooms >= filters.rooms_min)
        if filters.amenities:
            for index, amenity in enumerate(filters.amenities):
                stmt = stmt.where(self._amenity_clause(amenity, index))
        if filters.q:
            stmt = stmt.where(self._fulltext_clause(filters.q))
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

    def _apply_ranked_sort(self, stmt, filters: ListingFilters):
        """Order full-text results by ts_rank desc (Postgres only), then recency.

        Only applied when a keyword query is present and the caller kept the
        default sort. On PostgreSQL relevance ranking uses the same parameterised
        ``websearch_to_tsquery``. Any explicit sort takes precedence and is left
        untouched by returning ``None`` here.
        """
        if not filters.q or self._dialect != "postgresql":
            return None
        # ``text()`` yields a TextClause without ``.desc()``; bake the direction
        # into the SQL so it can be used directly in ORDER BY.
        rank_desc = text(
            "ts_rank(search_vector, websearch_to_tsquery('french', :q)) DESC"
        ).bindparams(q=filters.q)
        return stmt.order_by(
            rank_desc, Listing.published_at.desc(), Listing.created_at.desc()
        )

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

        is_default_sort = sort in (SortOption.newest, SortOption.date_desc)
        ranked = self._apply_ranked_sort(base, filters) if is_default_sort else None
        stmt = ranked if ranked is not None else self._apply_sort(base, sort)
        stmt = stmt.options(selectinload(Listing.photos))
        stmt = stmt.offset((page - 1) * size).limit(size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def list_all(
        self, status: ListingStatus | None, page: int, size: int
    ) -> tuple[list[Listing], int]:
        """Admin listing: every status, optionally filtered by one status."""
        stmt = select(Listing)
        count_stmt = select(func.count()).select_from(Listing)
        if status is not None:
            stmt = stmt.where(Listing.status == status)
            count_stmt = count_stmt.where(Listing.status == status)

        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = (
            stmt.order_by(Listing.created_at.desc())
            .options(selectinload(Listing.photos))
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total
