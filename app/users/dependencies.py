from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import StorageBackend, get_storage
from app.users.service import ProfileService


def get_profile_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> ProfileService:
    return ProfileService(session, storage)
