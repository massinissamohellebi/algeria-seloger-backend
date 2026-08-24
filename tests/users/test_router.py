"""Router tests for the epic-9 profile surface (/users/me*)."""

import pytest

from app.core.storage import InMemoryStorage, get_storage
from app.main import app
from tests._mailer import capturing_mailer

PW = "supersecret123"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


async def register_verified(client, email="profile@example.com"):
    """Register + verify a user and return (auth headers, refresh token)."""
    await client.post(
        "/auth/register",
        json={"email": email, "password": PW, "full_name": "Profile User"},
    )
    await client.post(
        "/auth/verify-email", json={"token": capturing_mailer.token_for(email)}
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": PW}
    )
    body = login.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["refresh_token"]


@pytest.fixture
def memory_storage():
    """Force the in-memory storage backend for avatar tests."""
    backend = InMemoryStorage()
    app.dependency_overrides[get_storage] = lambda: backend
    yield backend
    app.dependency_overrides.pop(get_storage, None)


# --- Profile + preferences (S1, S2) ----------------------------------------


@pytest.mark.asyncio
async def test_get_me_returns_profile_with_preferences(client):
    headers, _ = await register_verified(client)
    resp = await client.get("/users/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "profile@example.com"
    assert body["language"] == "fr"
    assert body["email_notifications"] is True
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_get_me_requires_auth(client):
    assert (await client.get("/users/me")).status_code == 401


@pytest.mark.asyncio
async def test_patch_me_updates_name_and_phone(client):
    headers, _ = await register_verified(client)
    resp = await client.patch(
        "/users/me", headers=headers, json={"full_name": "New Name", "phone": "0555"}
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "New Name"
    assert resp.json()["phone"] == "0555"


@pytest.mark.asyncio
async def test_patch_me_ignores_email_and_role(client):
    headers, _ = await register_verified(client)
    resp = await client.patch(
        "/users/me",
        headers=headers,
        json={"email": "hacker@evil.com", "role": "admin", "full_name": "Ok"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "profile@example.com"
    assert body["role"] == "particulier"
    assert body["full_name"] == "Ok"


@pytest.mark.asyncio
async def test_patch_preferences_persists(client):
    headers, _ = await register_verified(client)
    resp = await client.patch(
        "/users/me/preferences",
        headers=headers,
        json={"language": "ar", "email_notifications": False},
    )
    assert resp.status_code == 200
    assert resp.json()["language"] == "ar"
    assert resp.json()["email_notifications"] is False


@pytest.mark.asyncio
async def test_preferences_rejects_unknown_language(client):
    headers, _ = await register_verified(client)
    resp = await client.patch(
        "/users/me/preferences", headers=headers, json={"language": "es"}
    )
    assert resp.status_code == 422


# --- Change password (S3) --------------------------------------------------


@pytest.mark.asyncio
async def test_change_password_success_and_revokes_sessions(client):
    headers, refresh_token = await register_verified(client)
    resp = await client.post(
        "/users/me/change-password",
        headers=headers,
        json={"current_password": PW, "new_password": "brand-new-pass-1"},
    )
    assert resp.status_code == 204

    # The old refresh token is revoked (all sessions invalidated).
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refreshed.status_code == 401

    # New password works.
    login = await client.post(
        "/auth/login",
        json={"email": "profile@example.com", "password": "brand-new-pass-1"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current_rejected(client):
    headers, _ = await register_verified(client)
    resp = await client.post(
        "/users/me/change-password",
        headers=headers,
        json={"current_password": "wrong-pass-1", "new_password": "brand-new-pass-1"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_weak_rejected(client):
    headers, _ = await register_verified(client)
    resp = await client.post(
        "/users/me/change-password",
        headers=headers,
        json={"current_password": PW, "new_password": "short"},
    )
    assert resp.status_code == 422


# --- Avatar (S4) -----------------------------------------------------------


@pytest.mark.asyncio
async def test_avatar_upload_sets_url(client, memory_storage):
    headers, _ = await register_verified(client)
    resp = await client.post(
        "/users/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", PNG, "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["avatar_url"]
    assert len(memory_storage.objects) == 1


@pytest.mark.asyncio
async def test_avatar_upload_rejects_bad_mime(client, memory_storage):
    headers, _ = await register_verified(client)
    resp = await client.post(
        "/users/me/avatar",
        headers=headers,
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "unsupported_avatar_type"


@pytest.mark.asyncio
async def test_avatar_replace_then_delete(client, memory_storage):
    headers, _ = await register_verified(client)
    await client.post(
        "/users/me/avatar",
        headers=headers,
        files={"file": ("a.png", PNG, "image/png")},
    )
    # Replacing cleans up the previous object (still exactly one held).
    await client.post(
        "/users/me/avatar",
        headers=headers,
        files={"file": ("b.png", PNG, "image/png")},
    )
    assert len(memory_storage.objects) == 1

    resp = await client.delete("/users/me/avatar", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["avatar_url"] is None
    assert len(memory_storage.objects) == 0


# --- GDPR export + delete (S5) ---------------------------------------------


@pytest.mark.asyncio
async def test_export_contains_only_own_data(client):
    headers, _ = await register_verified(client)
    resp = await client.get("/users/me/export", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"]["email"] == "profile@example.com"
    assert "hashed_password" not in body["profile"]
    assert body["listings"] == []
    assert "exported_at" in body


@pytest.mark.asyncio
async def test_delete_account_is_irreversible(client):
    headers, _ = await register_verified(client)
    resp = await client.delete("/users/me", headers=headers)
    assert resp.status_code == 204

    # The token no longer resolves to a user, and login fails.
    assert (await client.get("/users/me", headers=headers)).status_code == 401
    login = await client.post(
        "/auth/login", json={"email": "profile@example.com", "password": PW}
    )
    assert login.status_code == 401
