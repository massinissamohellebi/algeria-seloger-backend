import uuid
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.favorites.repository import FavoriteRepository
from app.listings.exceptions import ListingNotFoundError
from app.listings.repository import ListingRepository
from app.listings.schemas import ListingPage
from app.listings.service import _to_summary


class FavoriteService:
    """Business logic for favourites. Every method scopes to ``current_user``
    (no user-id parameter), so a user can only touch their own favourites.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.repo = FavoriteRepository(session)
        self.listings = ListingRepository(session)

    async def _require_listing(self, listing_id: uuid.UUID) -> None:
        if await self.listings.get_by_id(listing_id) is None:
            raise ListingNotFoundError()

    async def add(self, user: User, listing_id: uuid.UUID) -> None:
        await self._require_listing(listing_id)
        await self.repo.add(user.id, listing_id)

    async def remove(self, user: User, listing_id: uuid.UUID) -> None:
        await self._require_listing(listing_id)
        await self.repo.remove(user.id, listing_id)

    async def list(self, user: User, page: int, size: int) -> ListingPage:
        listings, total = await self.repo.list_for_user(user.id, page, size)
        items = [_to_summary(listing) for listing in listings]
        for item in items:
            item.is_favorited = True
        return ListingPage(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=ceil(total / size) if size else 0,
        )
