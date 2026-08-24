import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.models import Notification, NotificationType


class NotificationRepository:
    """Data-access for in-app notifications (epic vacances)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        body: str | None = None,
        link: str | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            link=link,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def list_for_user(self, user_id: uuid.UUID, limit: int = 30) -> list[Notification]:
        result = await self.session.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def unread_count(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return int(result.scalar_one())

    async def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        return await self.session.get(Notification, notification_id)

    async def mark_read(self, notification: Notification) -> None:
        notification.is_read = True
        await self.session.flush()

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self.session.flush()
