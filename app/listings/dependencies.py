from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import StorageBackend, get_storage
from app.listings.repository import ListingRepository
from app.listings.service import ListingService, PhotoService


def get_listing_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ListingService:
    return ListingService(ListingRepository(session))


def get_photo_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> PhotoService:
    return PhotoService(ListingRepository(session), storage)
