import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    UUID,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.reference.models import UserStatusRef
from app.wilaya.models import Wilaya


class UserStatus(enum.StrEnum):
    """Moderation status of an account (epic 10)."""

    active = "active"
    suspended = "suspended"
    banned = "banned"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    wilaya_code: Mapped[str | None] = mapped_column(
        CHAR(2), ForeignKey("wilayas.code"), nullable=True
    )
    wilaya_ref: Mapped["Wilaya | None"] = relationship(lazy="selectin")
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    account_type: Mapped[str] = mapped_column(
        String(20), default="particulier", server_default="particulier", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    # Preferences (epic 9). Language is an allow-listed code (fr/en/ar);
    # email_notifications drives future transactional/notification emails.
    language: Mapped[str] = mapped_column(
        String(2), default="fr", server_default="fr", nullable=False
    )
    email_notifications: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    # Moderation status (epic 10): active / suspended / banned — FK to the
    # user_statuses reference table. Suspended is time-boxed via
    # `suspended_until`; banned is permanent.
    status: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("user_statuses.code"),
        default="active",
        server_default="active",
        nullable=False,
    )
    status_ref: Mapped["UserStatusRef"] = relationship(lazy="selectin")
    suspended_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @property
    def wilaya(self) -> str | None:
        """Localised wilaya name (FR) resolved via the FK, for read payloads."""
        return self.wilaya_ref.name_fr if self.wilaya_ref else None

    @property
    def role(self) -> str:
        """Canonical role derived from admin flag + account type.

        The DB keeps `account_type` (particulier/agence) and a separate
        `is_admin` flag; the epic's `role` concept is their union. Admin wins so
        an admin account is always surfaced as such.
        """
        if self.is_admin:
            return "admin"
        return self.account_type


class EmailVerificationToken(Base):
    """Single-use, hashed email-verification token (24h TTL).

    Only the SHA-256 hash of the opaque token is stored; the plaintext lives
    solely in the verification link emailed to the user.
    """

    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_email_verification_tokens_token_hash", "token_hash"),
    )


class PasswordResetToken(Base):
    """Single-use, hashed password-reset token (1h TTL). Hash-only at rest."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_password_reset_tokens_token_hash", "token_hash"),
    )


class RefreshToken(Base):
    """Opaque refresh token, hashed at rest, rotated on use.

    Rotation links each token to the one that replaced it (`replaced_by`) so a
    reuse of an already-rotated token can be detected and the whole family
    revoked. `revoked_at` marks logout / reset / reuse-invalidation.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_refresh_tokens_token_hash", "token_hash"),
        Index("ix_refresh_tokens_user_id", "user_id"),
    )


class LoginAttempt(Base):
    """One row per throttled attempt (login / forgot-password), keyed on the
    (ip, email) identifier, used to enforce a sliding-window rate limit.
    Successful logins purge the identifier's rows.
    """

    __tablename__ = "login_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    identifier: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_login_attempts_identifier_created_at", "identifier", "created_at"),
    )
