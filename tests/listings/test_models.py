import uuid

import pytest
from sqlalchemy import select

from app.auth.models import User
from app.core.security import hash_password
from app.listings.models import (
    Listing,
    ListingPhoto,
    ListingStatus,
    PriceUnit,
    PropertyType,
    TransactionType,
)


async def _make_owner(db_session) -> User:
    user = User(
        email=f"owner-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("supersecret123"),
        full_name="Owner",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_listing_persists_with_defaults(db_session):
    owner = await _make_owner(db_session)
    listing = Listing(
        owner_id=owner.id,
        title="Appartement F4 vue mer à Hydra",
        transaction_type=TransactionType.vente,
        property_type=PropertyType.appartement,
        price=45_000_000,
        price_unit=PriceUnit.DZD_total,
        wilaya="Alger",
    )
    db_session.add(listing)
    await db_session.flush()
    await db_session.refresh(listing)

    assert isinstance(listing.id, uuid.UUID)
    assert listing.status is ListingStatus.draft
    assert listing.furnished is False
    assert listing.amenities == []
    assert listing.created_at is not None


@pytest.mark.asyncio
async def test_delete_listing_cascades_photos(db_session):
    owner = await _make_owner(db_session)
    listing = Listing(
        owner_id=owner.id,
        title="Villa avec piscine",
        transaction_type=TransactionType.vente,
        property_type=PropertyType.villa,
        price=150_000_000,
        price_unit=PriceUnit.DZD_total,
        wilaya="Alger",
        amenities=["Piscine", "Jardin"],
        photos=[
            ListingPhoto(url="https://cdn/1.jpg", is_cover=True, position=0),
            ListingPhoto(url="https://cdn/2.jpg", position=1),
        ],
    )
    db_session.add(listing)
    await db_session.flush()
    listing_id = listing.id
    assert (await db_session.execute(select(ListingPhoto))).scalars().all()

    await db_session.delete(listing)
    await db_session.flush()

    remaining = (
        (
            await db_session.execute(
                select(ListingPhoto).where(ListingPhoto.listing_id == listing_id)
            )
        )
        .scalars()
        .all()
    )
    assert remaining == []


def test_composite_filter_index_declared():
    index_names = {ix.name for ix in Listing.__table__.indexes}
    assert "ix_listings_filter" in index_names
    filter_ix = next(ix for ix in Listing.__table__.indexes if ix.name == "ix_listings_filter")
    assert [c.name for c in filter_ix.columns] == [
        "status",
        "transaction_type",
        "property_type",
        "wilaya",
        "price",
    ]
