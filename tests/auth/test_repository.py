import pytest

from app.auth.repository import UserRepository


@pytest.mark.asyncio
async def test_create_and_get_by_email(db_session):
    repo = UserRepository(db_session)
    created = await repo.create(
        email="rania@example.com", hashed_password="hashed", full_name="Rania"
    )
    await db_session.commit()

    assert created.id is not None
    fetched = await repo.get_by_email("rania@example.com")
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.is_active is True


@pytest.mark.asyncio
async def test_get_by_email_missing_returns_none(db_session):
    repo = UserRepository(db_session)
    assert await repo.get_by_email("nobody@example.com") is None


@pytest.mark.asyncio
async def test_get_by_id(db_session):
    repo = UserRepository(db_session)
    created = await repo.create(
        email="karim@example.com", hashed_password="hashed", full_name=None
    )
    await db_session.commit()
    assert (await repo.get_by_id(created.id)).email == "karim@example.com"
