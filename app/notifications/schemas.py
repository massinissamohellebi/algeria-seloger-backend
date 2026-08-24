import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    body: str | None = None
    link: str | None = None
    is_read: bool
    created_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationRead]
    unread_count: int


class UnreadCount(BaseModel):
    unread_count: int
