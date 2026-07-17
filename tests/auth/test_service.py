import pytest

from app.auth.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.auth.repository import UserRepository
from app.auth.schemas import UserCreate
from app.auth.service import AuthService


@pytest.fixture
def service(db_session) -> AuthService:
    return AuthService(UserRepository(db_session))


@pytest.mark.asyncio
async def test_register_hashes_password(service, db_session):
    user = await service.register(
        UserCreate(email="new@example.com", password="password123", full_name="New")
    )
    await db_session.commit()
    assert user.hashed_password != "password123"
    assert user.email == "new@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email_raises(service, db_session):
    payload = UserCreate(email="dup@example.com", password="password123")
    await service.register(payload)
    await db_session.commit()
    with pytest.raises(EmailAlreadyExistsError):
        await service.register(payload)


@pytest.mark.asyncio
async def test_login_success_returns_token(service, db_session):
    await service.register(
        UserCreate(email="log@example.com", password="password123")
    )
    await db_session.commit()
    token = await service.login("log@example.com", "password123")
    assert token.access_token
    assert token.token_type == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_raises(service, db_session):
    await service.register(
        UserCreate(email="log2@example.com", password="password123")
    )
    await db_session.commit()
    with pytest.raises(InvalidCredentialsError):
        await service.login("log2@example.com", "wrongpass123")


@pytest.mark.asyncio
async def test_get_current_user_roundtrip(service, db_session):
    await service.register(
        UserCreate(email="cur@example.com", password="password123")
    )
    await db_session.commit()
    token = await service.login("cur@example.com", "password123")
    user = await service.get_current_user(token.access_token)
    assert user.email == "cur@example.com"


@pytest.mark.asyncio
async def test_get_current_user_bad_token_raises(service):
    with pytest.raises(InvalidTokenError):
        await service.get_current_user("not-a-jwt")
