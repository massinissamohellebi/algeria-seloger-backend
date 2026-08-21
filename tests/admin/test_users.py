"""Tests for admin user management + ban/suspend enforcement (Story 4)."""

import pytest
from sqlalchemy import select

from app.auth.models import User
from tests.listings.test_admin import admin_headers
from tests.listings.test_router import auth_headers

PW = "supersecret123"
FUTURE = "2099-01-01T00:00:00Z"


async def user_id(db_session, email: str) -> str:
    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    return str(user.id)


async def login(client, email: str):
    return await client.post("/auth/login", json={"email": email, "password": PW})


@pytest.mark.asyncio
async def test_admin_users_requires_admin(client):
    non_admin = await auth_headers(client, "user@example.com")
    assert (await client.get("/admin/users")).status_code == 401
    assert (await client.get("/admin/users", headers=non_admin)).status_code == 403


@pytest.mark.asyncio
async def test_list_users_returns_page(client, db_session):
    await auth_headers(client, "target@example.com")
    admin = await admin_headers(client, db_session)
    resp = await client.get("/admin/users", headers=admin)
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()["items"]}
    assert {"target@example.com", "admin@example.com"} <= emails


@pytest.mark.asyncio
async def test_suspend_rejects_login(client, db_session):
    await auth_headers(client, "target@example.com")
    admin = await admin_headers(client, db_session)
    tid = await user_id(db_session, "target@example.com")

    resp = await client.post(
        f"/admin/users/{tid}/suspend",
        json={"suspended_until": FUTURE},
        headers=admin,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"

    rejected = await login(client, "target@example.com")
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "account_suspended"


@pytest.mark.asyncio
async def test_ban_then_reactivate(client, db_session):
    await auth_headers(client, "target@example.com")
    admin = await admin_headers(client, db_session)
    tid = await user_id(db_session, "target@example.com")

    ban = await client.post(f"/admin/users/{tid}/ban", headers=admin)
    assert ban.status_code == 200 and ban.json()["status"] == "banned"
    assert (await login(client, "target@example.com")).status_code == 403

    react = await client.post(f"/admin/users/{tid}/reactivate", headers=admin)
    assert react.status_code == 200 and react.json()["status"] == "active"
    assert (await login(client, "target@example.com")).status_code == 200


@pytest.mark.asyncio
async def test_banned_user_blocked_on_authed_paths(client, db_session):
    target = await auth_headers(client, "target@example.com")
    admin = await admin_headers(client, db_session)
    tid = await user_id(db_session, "target@example.com")

    await client.post(f"/admin/users/{tid}/ban", headers=admin)
    # The still-unexpired access token is rejected on every authed path.
    me = await client.get("/users/me", headers=target)
    assert me.status_code == 403
    assert me.json()["error"]["code"] == "account_banned"


@pytest.mark.asyncio
async def test_admin_cannot_ban_self(client, db_session):
    admin = await admin_headers(client, db_session)
    aid = await user_id(db_session, "admin@example.com")
    resp = await client.post(f"/admin/users/{aid}/ban", headers=admin)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "cannot_moderate_self"
