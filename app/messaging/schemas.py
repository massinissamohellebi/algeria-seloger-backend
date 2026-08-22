import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    is_read: bool
    created_at: datetime


class ConversationStart(BaseModel):
    listing_id: uuid.UUID
    initial_message: str = Field(min_length=1, max_length=2000)


class ListingPreview(BaseModel):
    id: uuid.UUID
    title: str
    cover_url: str | None = None


class ConversationRead(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID | None
    enquirer_id: uuid.UUID
    owner_id: uuid.UUID
    updated_at: datetime
    listing: ListingPreview | None = None
    last_message: MessageRead | None = None
    unread_count: int = 0


class ConversationList(BaseModel):
    items: list[ConversationRead]
    total: int


class MessagePage(BaseModel):
    items: list[MessageRead]
    total: int
    page: int
    per_page: int


class UnreadCount(BaseModel):
    unread_count: int
