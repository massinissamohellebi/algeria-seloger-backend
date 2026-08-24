"""Aggregates all ORM models so Alembic's autogenerate sees them.

Import every feature's models here as new features are added.
"""

from app.auth.models import (  # noqa: F401
    EmailVerificationToken,
    LoginAttempt,
    PasswordResetToken,
    RefreshToken,
    User,
)
from app.favorites.models import Favorite  # noqa: F401
from app.listings.models import (  # noqa: F401
    Listing,
    ListingPhoto,
    ListingStatus,
    PriceUnit,
    PropertyType,
    TransactionType,
)
from app.messaging.models import Conversation, Message  # noqa: F401
from app.reference.models import (  # noqa: F401
    ReportReasonRef,
    ReportStatusRef,
    UserStatusRef,
)
from app.reports.models import Report  # noqa: F401
from app.wilaya.models import Wilaya  # noqa: F401
