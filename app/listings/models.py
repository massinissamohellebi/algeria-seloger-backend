import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    UUID,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionType(enum.StrEnum):
    vente = "vente"
    location = "location"
    colocation = "colocation"
    vacances = "vacances"


class PropertyType(enum.StrEnum):
    appartement = "appartement"
    villa = "villa"
    maison = "maison"
    studio = "studio"
    local_commercial = "local_commercial"
    terrain = "terrain"
    bureau = "bureau"
    immeuble = "immeuble"


class PriceUnit(enum.StrEnum):
    DZD_total = "DZD_total"
    DZD_month = "DZD_month"
    DZD_night = "DZD_night"


class ListingStatus(enum.StrEnum):
    draft = "draft"
    published = "published"
    moderated = "moderated"
    archived = "archived"


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type"), nullable=False
    )
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType, name="property_type"), nullable=False
    )

    price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price_unit: Mapped[PriceUnit] = mapped_column(
        Enum(PriceUnit, name="price_unit"), nullable=False
    )

    surface: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bedrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    furnished: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    amenities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    wilaya: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    neighbourhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus, name="listing_status"),
        default=ListingStatus.draft,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    photos: Mapped[list["ListingPhoto"]] = relationship(
        back_populates="listing",
        cascade="all, delete-orphan",
        order_by="ListingPhoto.position",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ix_listings_filter",
            "status",
            "transaction_type",
            "property_type",
            "wilaya",
            "price",
        ),
    )


class ListingPhoto(Base):
    __tablename__ = "listing_photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    listing: Mapped["Listing"] = relationship(back_populates="photos")
