import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.notifications.dependencies import get_notification_service
from app.notifications.schemas import NotificationList, UnreadCount
from app.notifications.service import NotificationService

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[NotificationService, Depends(get_notification_service)]

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationList)
async def list_notifications(
    current_user: CurrentUser,
    service: ServiceDep,
) -> NotificationList:
    return await service.list_notifications(current_user)


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    current_user: CurrentUser,
    service: ServiceDep,
) -> UnreadCount:
    return UnreadCount(unread_count=await service.unread_count(current_user))


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> None:
    await service.mark_read(notification_id, current_user)
    await session.commit()


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> None:
    await service.mark_all_read(current_user)
    await session.commit()
