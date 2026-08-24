import uuid

from pydantic import BaseModel


class FavoriteState(BaseModel):
    """Result of a toggle — mirrors the `is_favorited` flag on listings."""

    listing_id: uuid.UUID
    is_favorited: bool
