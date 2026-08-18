"""Service-level tests for token edge cases that are awkward to reach over
HTTP: expiry and verify-email idempotency with multiple outstanding tokens."""

from datetime import UTC, datetime, timedelta

import pytest

from app.auth.exceptions import (
    InvalidResetTokenError,
    InvalidVerificationTokenError,
)
from app.auth.repository import UserRepository
from app.auth.schemas import UserCreate
from app.auth.service import AuthService
from app.core.security import generate_opaque_token, hash_token

PW = "test-" + "pw-1234"
NEW_PW = "test-" + "pw-5678"


@pytest.fixture
def service(db_session) -> AuthService:
    return AuthService(UserRepository(db_session))


async def _make_user(service, db_session, email="tok@example.com"):
    user = await service.register(
        UserCreate(email=email, password=PW, full_name="Tok")
    )
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_expired_verification_token_is_rejected(service, db_session):
    user = await _make_user(service, db_session)
    plaintext = generate_opaque_token()
    await service.verification_tokens.create(
        user_id=user.id,
        token_hash=hash_token(plaintext),
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    await db_session.commit()
    with pytest.raises(InvalidVerificationTokenError):
        await service.verify_email(plaintext)


@pytest.mark.asyncio
async def test_expired_reset_token_is_rejected(service, db_session):
    user = await _make_user(service, db_session)
    plaintext = generate_opaque_token()
    await service.reset_tokens.create(
        user_id=user.id,
        token_hash=hash_token(plaintext),
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    await db_session.commit()
    with pytest.raises(InvalidResetTokenError):
        await service.reset_password(plaintext, NEW_PW)


@pytest.mark.asyncio
async def test_verify_email_is_idempotent_with_second_token(service, db_session):
    """A still-valid token presented after the account is already verified is a
    no-op success (never toggles state back)."""
    user = await _make_user(service, db_session)
    first = generate_opaque_token()
    second = generate_opaque_token()
    future = datetime.now(UTC) + timedelta(hours=1)
    await service.verification_tokens.create(
        user_id=user.id, token_hash=hash_token(first), expires_at=future
    )
    await service.verification_tokens.create(
        user_id=user.id, token_hash=hash_token(second), expires_at=future
    )
    await db_session.commit()

    await service.verify_email(first)
    await db_session.commit()
    # Second, still-valid token: no error, still verified.
    await service.verify_email(second)
    await db_session.commit()

    refreshed = await service.repository.get_by_id(user.id)
    assert refreshed.is_email_verified is True
