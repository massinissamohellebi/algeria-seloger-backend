from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.messaging.service import MessagingService


def get_messaging_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MessagingService:
    return MessagingService(session)
