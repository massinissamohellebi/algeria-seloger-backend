import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.favorites.models import Favorite
from app.listings.models import Listing


class FavoriteRepository:
    """Data-access for user favourites."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists(self, user_id: uuid.UUID, listing_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(Favorite.id).where(
                Favorite.user_id == user_id,
                Favorite.listing_id == listing_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def add(self, user_id: uuid.UUID, listing_id: uuid.UUID) -> None:
        """Idempotent insert — a repeat call is a no-op (unique constraint)."""
        if await self.exists(user_id, listing_id):
            return
        self.session.add(Favorite(user_id=user_id, listing_id=listing_id))
        await self.session.flush()

    async def remove(self, user_id: uuid.UUID, listing_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.listing_id == listing_id,
            )
        )
        await self.session.flush()

    async def favorited_ids(
        self, user_id: uuid.UUID, listing_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        """Batch lookup: which of ``listing_ids`` the user has favourited."""
        if not listing_ids:
            return set()
        result = await self.session.execute(
            select(Favorite.listing_id).where(
                Favorite.user_id == user_id,
                Favorite.listing_id.in_(listing_ids),
            )
        )
        return set(result.scalars())

    async def list_for_user(
        self, user_id: uuid.UUID, page: int, size: int
    ) -> tuple[list[Listing], int]:
        """Return (listings, total) the user saved, newest-saved first."""
        count_stmt = (
            select(func.count())
            .select_from(Favorite)
            .where(Favorite.user_id == user_id)
        )
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            select(Listing)
            .join(Favorite, Favorite.listing_id == Listing.id)
            .where(Favorite.user_id == user_id)
            .options(selectinload(Listing.photos))
            .order_by(Favorite.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        listings = list((await self.session.execute(stmt)).scalars())
        return listings, int(total)
