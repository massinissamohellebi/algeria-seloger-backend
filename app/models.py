"""Aggregates all ORM models so Alembic's autogenerate sees them.

Import every feature's models here as new features are added.
"""

from app.auth.models import User  # noqa: F401
from app.listings.models import (  # noqa: F401
    Listing,
    ListingPhoto,
    ListingStatus,
    PriceUnit,
    PropertyType,
    TransactionType,
)
from app.wilaya.models import Wilaya  # noqa: F401
