import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewRead(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    rating: int
    comment: str | None = None
    created_at: datetime


class ReviewAggregate(BaseModel):
    average: float | None = None
    count: int = 0
    coup_de_coeur: bool = False


class ReviewList(ReviewAggregate):
    items: list[ReviewRead]
