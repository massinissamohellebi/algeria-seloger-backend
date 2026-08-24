import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.notifications.exceptions import (
    NotificationNotFoundError,
    NotOwnNotificationError,
)
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import NotificationList, NotificationRead


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)

    async def list_notifications(self, user: User) -> NotificationList:
        items = await self.repo.list_for_user(user.id)
        unread = await self.repo.unread_count(user.id)
        return NotificationList(
            items=[NotificationRead.model_validate(n) for n in items],
            unread_count=unread,
        )

    async def unread_count(self, user: User) -> int:
        return await self.repo.unread_count(user.id)

    async def mark_read(self, notification_id: uuid.UUID, user: User) -> None:
        notification = await self.repo.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFoundError()
        if notification.user_id != user.id:
            raise NotOwnNotificationError()
        await self.repo.mark_read(notification)

    async def mark_all_read(self, user: User) -> None:
        await self.repo.mark_all_read(user.id)
