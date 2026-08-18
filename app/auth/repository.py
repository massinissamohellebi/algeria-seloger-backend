import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import (
    EmailVerificationToken,
    LoginAttempt,
    PasswordResetToken,
    RefreshToken,
    User,
)


class UserRepository:
    """Data-access layer for the User model."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str | None,
        phone: str | None = None,
        account_type: str = "particulier",
    ) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            phone=phone,
            account_type=account_type,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update(self, user: User, data: dict) -> User:
        for key, value in data.items():
            setattr(user, key, value)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.flush()


class EmailVerificationTokenRepository:
    """Data-access for single-use email-verification tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        result = await self.session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def consume(self, token: EmailVerificationToken, *, now: datetime) -> None:
        token.consumed_at = now
        await self.session.flush()

    async def delete_unconsumed_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.consumed_at.is_(None),
            )
        )
        await self.session.flush()


class PasswordResetTokenRepository:
    """Data-access for single-use password-reset tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        token = PasswordResetToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def consume(self, token: PasswordResetToken, *, now: datetime) -> None:
        token.consumed_at = now
        await self.session.flush()

    async def delete_unconsumed_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.consumed_at.is_(None),
            )
        )
        await self.session.flush()


class RefreshTokenRepository:
    """Data-access for opaque, rotating refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(
        self,
        token: RefreshToken,
        *,
        now: datetime,
        replaced_by: uuid.UUID | None = None,
    ) -> None:
        token.revoked_at = now
        if replaced_by is not None:
            token.replaced_by = replaced_by
        await self.session.flush()

    async def revoke_all_for_user(
        self, user_id: uuid.UUID, *, now: datetime
    ) -> None:
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for token in result.scalars():
            token.revoked_at = now
        await self.session.flush()


class LoginAttemptRepository:
    """Sliding-window counter for login / forgot-password rate limiting."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, identifier: str) -> None:
        self.session.add(LoginAttempt(identifier=identifier))
        await self.session.flush()

    async def count_since(self, identifier: str, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.identifier == identifier,
                LoginAttempt.created_at >= since,
            )
        )
        return int(result.scalar_one())

    async def oldest_since(
        self, identifier: str, since: datetime
    ) -> datetime | None:
        result = await self.session.execute(
            select(func.min(LoginAttempt.created_at)).where(
                LoginAttempt.identifier == identifier,
                LoginAttempt.created_at >= since,
            )
        )
        return result.scalar_one_or_none()

    async def clear(self, identifier: str) -> None:
        await self.session.execute(
            delete(LoginAttempt).where(LoginAttempt.identifier == identifier)
        )
        await self.session.flush()
