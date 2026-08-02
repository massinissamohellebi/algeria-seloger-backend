from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.listings.repository import ListingRepository
from app.listings.service import ListingService


def get_listing_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ListingService:
    return ListingService(ListingRepository(session))
