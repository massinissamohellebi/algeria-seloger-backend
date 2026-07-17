import pytest


@pytest.mark.asyncio
async def test_register_returns_201(client, user_payload):
    resp = await client.post("/auth/register", json=user_payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == user_payload["email"]
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_register_duplicate_returns_409(client, user_payload):
    await client.post("/auth/register", json=user_payload)
    resp = await client.post("/auth/register", json=user_payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_already_exists"


@pytest.mark.asyncio
async def test_login_and_me_flow(client, user_payload):
    await client.post("/auth/register", json=user_payload)
    login = await client.post(
        "/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == user_payload["email"]


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(client, user_payload):
    await client.post("/auth/register", json=user_payload)
    resp = await client.post(
        "/auth/login",
        json={"email": user_payload["email"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_me_without_token_returns_403(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(client):
    resp = await client.get(
        "/auth/me", headers={"Authorization": "Bearer garbage"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_and_ready(client):
    assert (await client.get("/health")).status_code == 200
