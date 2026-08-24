from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.favorites.repository import FavoriteRepository
from app.favorites.service import FavoriteService


def get_favorite_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FavoriteService:
    return FavoriteService(session)


def get_favorite_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FavoriteRepository:
    return FavoriteRepository(session)
