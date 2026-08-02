import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.listings.models import (
    ListingStatus,
    PriceUnit,
    PropertyType,
    TransactionType,
)


class SortOption(enum.StrEnum):
    newest = "newest"
    price_asc = "price_asc"
    price_desc = "price_desc"
    surface_asc = "surface_asc"
    surface_desc = "surface_desc"


class PhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    is_cover: bool
    position: int


class ListingBase(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    transaction_type: TransactionType
    property_type: PropertyType
    price: int = Field(gt=0)
    price_unit: PriceUnit
    surface: int | None = Field(default=None, ge=0)
    rooms: int | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    floor: int | None = None
    furnished: bool = False
    amenities: list[str] = Field(default_factory=list)
    wilaya: str = Field(min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    neighbourhood: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    lat: float | None = None
    lng: float | None = None


class ListingCreate(ListingBase):
    pass


class ListingUpdate(BaseModel):
    """All fields optional for partial updates."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    transaction_type: TransactionType | None = None
    property_type: PropertyType | None = None
    price: int | None = Field(default=None, gt=0)
    price_unit: PriceUnit | None = None
    surface: int | None = Field(default=None, ge=0)
    rooms: int | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    floor: int | None = None
    furnished: bool | None = None
    amenities: list[str] | None = None
    wilaya: str | None = Field(default=None, min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    neighbourhood: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    lat: float | None = None
    lng: float | None = None


class ListingRead(ListingBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    photos: list[PhotoRead] = Field(default_factory=list)


class ListingSummary(BaseModel):
    """Lightweight listing shape for grid/list views."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    transaction_type: TransactionType
    property_type: PropertyType
    price: int
    price_unit: PriceUnit
    surface: int | None
    rooms: int | None
    bedrooms: int | None
    furnished: bool
    wilaya: str
    city: str | None
    status: str
    published_at: datetime | None
    created_at: datetime
    cover_url: str | None = None


class ListingPage(BaseModel):
    items: list[ListingSummary]
    total: int
    page: int
    size: int
    pages: int


class AdminStatusUpdate(BaseModel):
    status: ListingStatus
