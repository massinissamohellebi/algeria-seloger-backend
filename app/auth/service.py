import uuid
from datetime import UTC, datetime, timedelta

from app.auth.exceptions import (
    AccountBannedError,
    AccountSuspendedError,
    EmailAlreadyExistsError,
    EmailNotVerifiedError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidResetTokenError,
    InvalidTokenError,
    InvalidVerificationTokenError,
    RateLimitedError,
)
from app.auth.models import (
    EmailVerificationToken,
    PasswordResetToken,
    User,
    UserStatus,
)
from app.auth.repository import (
    EmailVerificationTokenRepository,
    LoginAttemptRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.auth.schemas import Token, UserCreate, UserUpdate
from app.core.config import settings
from app.core.mailer import (
    ConsoleMailer,
    Mailer,
    build_password_reset_email,
    build_verification_email,
)
from app.core.security import (
    JWTError,
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    """Coerce a possibly-naive datetime (SQLite loses tzinfo) to aware UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


class AuthService:
    """Business logic for authentication and user identity."""

    def __init__(
        self, repository: UserRepository, mailer: Mailer | None = None
    ) -> None:
        self.repository = repository
        self.session = repository.session
        self.mailer = mailer or ConsoleMailer()
        self.verification_tokens = EmailVerificationTokenRepository(self.session)
        self.reset_tokens = PasswordResetTokenRepository(self.session)
        self.refresh_tokens = RefreshTokenRepository(self.session)
        self.login_attempts = LoginAttemptRepository(self.session)

    # --- Registration / profile --------------------------------------------

    async def register(self, payload: UserCreate) -> User:
        existing = await self.repository.get_by_email(payload.email)
        if existing is not None:
            raise EmailAlreadyExistsError()
        user = await self.repository.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            phone=payload.phone,
            account_type=payload.account_type,
        )
        await self._issue_and_send_verification(user)
        return user

    async def update_profile(self, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        return await self.repository.update(user, data)

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError()
        await self.repository.update(
            user, {"hashed_password": hash_password(new_password)}
        )

    async def delete_account(self, user: User) -> None:
        await self.repository.delete(user)

    # --- Email verification (Story 2) --------------------------------------

    async def _issue_and_send_verification(self, user: User) -> None:
        plaintext = generate_opaque_token()
        expires_at = _now() + timedelta(hours=settings.email_verification_ttl_hours)
        await self.verification_tokens.create(
            user_id=user.id, token_hash=hash_token(plaintext), expires_at=expires_at
        )
        link = f"{settings.frontend_base_url}/auth/verify-email?token={plaintext}"
        subject, body = build_verification_email(link)
        await self.mailer.send(to=user.email, subject=subject, body=body)

    async def verify_email(self, token: str) -> None:
        record = await self._resolve_active_token(
            self.verification_tokens, token, InvalidVerificationTokenError
        )
        user = await self.repository.get_by_id(record.user_id)
        if user is None:
            raise InvalidVerificationTokenError()
        # Idempotent: an already-verified user just consumes the token, no toggle.
        if not user.is_email_verified:
            await self.repository.update(user, {"is_email_verified": True})
        await self.verification_tokens.consume(record, now=_now())

    async def resend_verification(self, email: str) -> None:
        # Enumeration-safe: always succeeds; only acts for an unverified user.
        user = await self.repository.get_by_email(email)
        if user is None or user.is_email_verified:
            return
        await self.verification_tokens.delete_unconsumed_for_user(user.id)
        await self._issue_and_send_verification(user)

    # --- Forgot / reset password (Story 3) ---------------------------------

    async def forgot_password(self, email: str, *, ip: str | None) -> None:
        identifier = _forgot_identifier(ip, email)
        await self._enforce_rate_limit(identifier)
        await self.login_attempts.add(identifier)
        # Enumeration-safe: always returns; only emails an existing user.
        user = await self.repository.get_by_email(email)
        if user is None:
            return
        await self.reset_tokens.delete_unconsumed_for_user(user.id)
        plaintext = generate_opaque_token()
        expires_at = _now() + timedelta(hours=settings.password_reset_ttl_hours)
        await self.reset_tokens.create(
            user_id=user.id, token_hash=hash_token(plaintext), expires_at=expires_at
        )
        link = f"{settings.frontend_base_url}/auth/reset-password?token={plaintext}"
        subject, body = build_password_reset_email(link)
        await self.mailer.send(to=user.email, subject=subject, body=body)

    async def reset_password(self, token: str, new_password: str) -> None:
        record = await self._resolve_active_token(
            self.reset_tokens, token, InvalidResetTokenError
        )
        user = await self.repository.get_by_id(record.user_id)
        if user is None:
            raise InvalidResetTokenError()
        await self.repository.update(
            user, {"hashed_password": hash_password(new_password)}
        )
        await self.reset_tokens.consume(record, now=_now())
        # Any leftover reset links + every active session are invalidated.
        await self.reset_tokens.delete_unconsumed_for_user(user.id)
        await self.refresh_tokens.revoke_all_for_user(user.id, now=_now())

    # --- Login / refresh / logout (Story 4 + 5) ----------------------------

    async def login(
        self, email: str, password: str, *, ip: str | None = None
    ) -> Token:
        identifier = _login_identifier(ip, email)
        await self._enforce_rate_limit(identifier)
        user = await self.repository.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            await self.login_attempts.add(identifier)
            raise InvalidCredentialsError()
        # Credentials are valid → clear the failure counter for this ip/email.
        await self.login_attempts.clear(identifier)
        if not user.is_active:
            raise InactiveUserError()
        # Unverified accounts cannot sign in — they must confirm their email
        # first (the client offers to resend the verification link).
        if not user.is_email_verified:
            raise EmailNotVerifiedError()
        _assert_not_moderated(user)
        return await self._issue_token_pair(user)

    async def refresh(self, refresh_token: str) -> Token:
        record = await self.refresh_tokens.get_by_hash(hash_token(refresh_token))
        if record is None:
            raise InvalidRefreshTokenError()
        if record.revoked_at is not None:
            # Reuse of an already-rotated token: invalidate the whole family.
            await self.refresh_tokens.revoke_all_for_user(record.user_id, now=_now())
            raise InvalidRefreshTokenError()
        if _aware(record.expires_at) <= _now():
            raise InvalidRefreshTokenError()
        user = await self.repository.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError()
        pair = await self._issue_token_pair(user)
        new_record = await self.refresh_tokens.get_by_hash(
            hash_token(pair.refresh_token or "")
        )
        await self.refresh_tokens.revoke(
            record, now=_now(), replaced_by=new_record.id if new_record else None
        )
        return pair

    async def logout(self, refresh_token: str) -> None:
        record = await self.refresh_tokens.get_by_hash(hash_token(refresh_token))
        # Idempotent: unknown / already-revoked tokens are a no-op.
        if record is not None and record.revoked_at is None:
            await self.refresh_tokens.revoke(record, now=_now())

    # --- Token helpers ------------------------------------------------------

    async def _issue_token_pair(self, user: User) -> Token:
        access = create_access_token(subject=str(user.id))
        plaintext = generate_opaque_token()
        expires_at = _now() + timedelta(days=settings.refresh_token_expire_days)
        await self.refresh_tokens.create(
            user_id=user.id, token_hash=hash_token(plaintext), expires_at=expires_at
        )
        return Token(access_token=access, refresh_token=plaintext)

    async def _resolve_active_token(
        self,
        repo: EmailVerificationTokenRepository | PasswordResetTokenRepository,
        token: str,
        error: type[Exception],
    ) -> EmailVerificationToken | PasswordResetToken:
        record = await repo.get_by_hash(hash_token(token))
        if (
            record is None
            or record.consumed_at is not None
            or _aware(record.expires_at) <= _now()
        ):
            raise error()
        return record

    # --- Rate limiting (Story 5) -------------------------------------------

    async def _enforce_rate_limit(self, identifier: str) -> None:
        window = timedelta(minutes=settings.login_rate_limit_window_minutes)
        since = _now() - window
        count = await self.login_attempts.count_since(identifier, since)
        if count < settings.login_rate_limit_max_attempts:
            return
        oldest = await self.login_attempts.oldest_since(identifier, since)
        retry_after = settings.login_rate_limit_window_minutes * 60
        if oldest is not None:
            reset_at = _aware(oldest) + window
            retry_after = max(1, int((reset_at - _now()).total_seconds()))
        raise RateLimitedError(retry_after=retry_after)

    # --- Current user -------------------------------------------------------

    async def get_current_user(self, token: str) -> User:
        user = await self._resolve_user_from_token(token)
        if not user.is_active:
            raise InactiveUserError()
        # Banned/suspended accounts are rejected on every authed path, so an
        # existing access token can't be used to keep acting after a ban.
        _assert_not_moderated(user)
        return user

    async def _resolve_user_from_token(self, token: str) -> User:
        user_id = _extract_subject(token)
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise InvalidTokenError()
        return user


def _assert_not_moderated(user: User) -> None:
    """Block banned users always, and suspended users until their date."""
    if user.status == UserStatus.banned:
        raise AccountBannedError()
    if user.status == UserStatus.suspended and (
        user.suspended_until is None or _aware(user.suspended_until) > _now()
    ):
        raise AccountSuspendedError()


def _login_identifier(ip: str | None, email: str) -> str:
    return f"login:{ip or 'unknown'}|{email.strip().lower()}"


def _forgot_identifier(ip: str | None, email: str) -> str:
    return f"forgot:{ip or 'unknown'}|{email.strip().lower()}"


def _extract_subject(token: str) -> uuid.UUID:
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise InvalidTokenError() from exc
    subject = payload.get("sub")
    if subject is None:
        raise InvalidTokenError()
    try:
        return uuid.UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError() from exc
