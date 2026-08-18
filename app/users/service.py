import contextlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import InvalidCredentialsError
from app.auth.models import User
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.core.security import hash_password, verify_password
from app.core.storage import StorageBackend, build_avatar_key
from app.listings.models import Listing
from app.users.exceptions import (
    AvatarTooLargeError,
    EmptyAvatarError,
    UnsupportedAvatarTypeError,
)
from app.users.schemas import PreferencesUpdate, ProfileUpdate

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024


class ProfileService:
    """Business logic for the authenticated user's own profile (epic 9).

    Every method operates on the passed ``current_user`` — there are no user-id
    parameters, so IDOR is impossible by construction.
    """

    def __init__(self, session: AsyncSession, storage: StorageBackend) -> None:
        self.session = session
        self.storage = storage
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    # --- Profile + preferences (S1, S2) ------------------------------------

    async def update_profile(self, user: User, payload: ProfileUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        return await self.users.update(user, data)

    async def update_preferences(
        self, user: User, payload: PreferencesUpdate
    ) -> User:
        data = payload.model_dump(exclude_unset=True)
        return await self.users.update(user, data)

    # --- Change password (S3) ----------------------------------------------

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError()
        await self.users.update(
            user, {"hashed_password": hash_password(new_password)}
        )
        # Invalidate every active session so a stolen/old token can't be reused.
        await self.refresh_tokens.revoke_all_for_user(
            user.id, now=datetime.now(UTC)
        )

    # --- Avatar (S4) --------------------------------------------------------

    async def upload_avatar(
        self, user: User, data: bytes, content_type: str
    ) -> User:
        if content_type not in ALLOWED_AVATAR_TYPES:
            raise UnsupportedAvatarTypeError()
        if not data:
            raise EmptyAvatarError()
        if len(data) > MAX_AVATAR_BYTES:
            raise AvatarTooLargeError()

        key = build_avatar_key(user.id, content_type)
        url = await self.storage.upload(key, data, content_type)
        previous = user.avatar_url
        await self.users.update(user, {"avatar_url": url})
        await self._cleanup_object(previous)
        return user

    async def remove_avatar(self, user: User) -> User:
        previous = user.avatar_url
        if previous is not None:
            await self.users.update(user, {"avatar_url": None})
            await self._cleanup_object(previous)
        return user

    # --- GDPR export + delete (S5) -----------------------------------------

    async def export_data(self, user: User) -> dict:
        result = await self.session.execute(
            select(Listing).where(Listing.owner_id == user.id)
        )
        listings = [
            {
                "id": str(listing.id),
                "title": listing.title,
                "transaction_type": listing.transaction_type.value,
                "property_type": listing.property_type.value,
                "status": listing.status.value,
                "price": listing.price,
                "wilaya": listing.wilaya,
                "city": listing.city,
                "created_at": listing.created_at.isoformat(),
            }
            for listing in result.scalars()
        ]
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "profile": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "avatar_url": user.avatar_url,
                "wilaya": user.wilaya,
                "bio": user.bio,
                "account_type": user.account_type,
                "role": user.role,
                "language": user.language,
                "email_notifications": user.email_notifications,
                "is_email_verified": user.is_email_verified,
                "created_at": user.created_at.isoformat(),
            },
            "listings": listings,
            # No messaging feature yet — kept for a stable export shape.
            "conversations": [],
        }

    async def delete_account(self, user: User) -> None:
        # Best-effort cleanup of the avatar object before the row disappears.
        await self._cleanup_object(user.avatar_url)
        # Hard delete; FKs cascade to tokens, listings and their photos, which
        # also revokes every session (refresh tokens are gone).
        await self.users.delete(user)

    # --- Helpers ------------------------------------------------------------

    async def _cleanup_object(self, url: str | None) -> None:
        if not url:
            return
        # Best-effort: a failed cleanup must never break the profile operation.
        with contextlib.suppress(Exception):
            await self.storage.delete(url)
