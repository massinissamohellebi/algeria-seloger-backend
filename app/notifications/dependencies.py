from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.notifications.service import NotificationService


def get_notification_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationService:
    return NotificationService(session)
