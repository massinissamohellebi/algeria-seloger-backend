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
    # Spec alias for the default recency sort (published_at desc). Kept alongside
    # `newest` so the existing frontend contract (`newest`) is not broken while
    # accepting the spec's canonical `date_desc` value too.
    date_desc = "date_desc"
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
    # Vacation-rental fields (used when transaction_type = vacances).
    max_guests: int | None = Field(default=None, ge=1, le=50)
    beds: int | None = Field(default=None, ge=0)
    pets_allowed: bool | None = None
    checkin_from: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    checkin_to: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    checkout_before: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    amenities: list[str] = Field(default_factory=list)
    wilaya: str = Field(min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    neighbourhood: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    lat: float | None = None
    lng: float | None = None
    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=32)


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
    max_guests: int | None = Field(default=None, ge=1, le=50)
    beds: int | None = Field(default=None, ge=0)
    pets_allowed: bool | None = None
    checkin_from: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    checkin_to: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    checkout_before: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    amenities: list[str] | None = None
    wilaya: str | None = Field(default=None, min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    neighbourhood: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=255)
    lat: float | None = None
    lng: float | None = None
    contact_name: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=32)


class ListingRead(ListingBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    photos: list[PhotoRead] = Field(default_factory=list)
    # Resolved per-request for the authenticated caller (epic 11).
    is_favorited: bool = False
    # Review aggregate (epic vacances), resolved per-request on detail.
    rating_avg: float | None = None
    review_count: int = 0


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
    # Resolved per-request for the authenticated caller (epic 11).
    is_favorited: bool = False


class ListingPage(BaseModel):
    items: list[ListingSummary]
    total: int
    page: int
    size: int
    pages: int


class AdminListingSummary(ListingSummary):
    """Listing summary enriched with owner info for the moderation panel."""

    owner_name: str | None = None
    owner_email: str | None = None


class AdminListingPage(BaseModel):
    items: list[AdminListingSummary]
    total: int
    page: int
    size: int
    pages: int


class AdminStatusUpdate(BaseModel):
    status: ListingStatus
