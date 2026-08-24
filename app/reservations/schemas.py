import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ReservationCreate(BaseModel):
    check_in: date
    check_out: date
    guests: int = Field(default=1, ge=1)


class ListingPreview(BaseModel):
    id: uuid.UUID
    title: str
    cover_url: str | None = None


class ReservationRead(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    listing: ListingPreview | None = None
    guest_id: uuid.UUID
    guest_name: str
    host_id: uuid.UUID
    check_in: date
    check_out: date
    guests: int
    status: str
    created_at: datetime


class ReservationList(BaseModel):
    items: list[ReservationRead]
    total: int
