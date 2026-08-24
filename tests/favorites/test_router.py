"""Router tests for the favourites feature (epic 11)."""

import uuid

import pytest

from tests._mailer import capturing_mailer

PW = "supersecret123"


async def authed(client, email: str) -> dict:
    await client.post(
        "/auth/register", json={"email": email, "password": PW, "full_name": "U"}
    )
    await client.post(
        "/auth/verify-email", json={"token": capturing_mailer.token_for(email)}
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": PW}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def listing_payload(**overrides) -> dict:
    payload = {
        "title": "Appartement F3 Alger",
        "description": "Lumineux.",
        "transaction_type": "vente",
        "property_type": "appartement",
        "price": 12_000_000,
        "price_unit": "DZD_total",
        "surface": 90,
        "rooms": 3,
        "wilaya": "Alger",
        "city": "Hydra",
    }
    payload.update(overrides)
    return payload


async def make_listing(client, headers, *, publish=True, **overrides) -> str:
    resp = await client.post(
        "/listings", json=listing_payload(**overrides), headers=headers
    )
    assert resp.status_code == 201, resp.text
    listing_id = resp.json()["id"]
    if publish:
        await client.post(f"/listings/{listing_id}/publish", headers=headers)
    return listing_id


@pytest.mark.asyncio
async def test_add_favorite_is_idempotent(client):
    headers = await authed(client, "fav@example.com")
    lid = await make_listing(client, headers)

    r1 = await client.post(f"/favorites/{lid}", headers=headers)
    r2 = await client.post(f"/favorites/{lid}", headers=headers)
    assert r1.status_code == 200 and r1.json()["is_favorited"] is True
    assert r2.status_code == 200

    listed = await client.get("/favorites", headers=headers)
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == lid
    assert listed.json()["items"][0]["is_favorited"] is True


@pytest.mark.asyncio
async def test_remove_favorite_is_idempotent(client):
    headers = await authed(client, "fav2@example.com")
    lid = await make_listing(client, headers)
    await client.post(f"/favorites/{lid}", headers=headers)

    d1 = await client.delete(f"/favorites/{lid}", headers=headers)
    d2 = await client.delete(f"/favorites/{lid}", headers=headers)
    assert d1.status_code == 200 and d1.json()["is_favorited"] is False
    assert d2.status_code == 200

    listed = await client.get("/favorites", headers=headers)
    assert listed.json()["total"] == 0


@pytest.mark.asyncio
async def test_favorite_nonexistent_listing_returns_404(client):
    headers = await authed(client, "fav3@example.com")
    resp = await client.post(f"/favorites/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "listing_not_found"


@pytest.mark.asyncio
async def test_favorites_require_auth(client):
    lid = uuid.uuid4()
    assert (await client.get("/favorites")).status_code == 401
    assert (await client.post(f"/favorites/{lid}")).status_code == 401
    assert (await client.delete(f"/favorites/{lid}")).status_code == 401


@pytest.mark.asyncio
async def test_favorites_are_scoped_to_current_user(client):
    owner = await authed(client, "owner@example.com")
    other = await authed(client, "other@example.com")
    lid = await make_listing(client, owner)
    await client.post(f"/favorites/{lid}", headers=owner)

    # The other user sees none of the owner's favourites.
    listed = await client.get("/favorites", headers=other)
    assert listed.json()["total"] == 0


@pytest.mark.asyncio
async def test_is_favorited_flag_on_listing_list_and_detail(client):
    headers = await authed(client, "flag@example.com")
    lid = await make_listing(client, headers)
    await client.post(f"/favorites/{lid}", headers=headers)

    # Authenticated list + detail expose is_favorited = true.
    listed = await client.get("/listings", headers=headers)
    item = next(i for i in listed.json()["items"] if i["id"] == lid)
    assert item["is_favorited"] is True
    detail = await client.get(f"/listings/{lid}", headers=headers)
    assert detail.json()["is_favorited"] is True

    # Anonymous callers always get false.
    anon = await client.get("/listings")
    anon_item = next(i for i in anon.json()["items"] if i["id"] == lid)
    assert anon_item["is_favorited"] is False


@pytest.mark.asyncio
async def test_favorites_list_is_paginated(client):
    headers = await authed(client, "page@example.com")
    ids = [await make_listing(client, headers, title=f"Annonce {i}") for i in range(3)]
    for lid in ids:
        await client.post(f"/favorites/{lid}", headers=headers)

    first = await client.get("/favorites?page=1&size=2", headers=headers)
    body = first.json()
    assert body["total"] == 3
    assert body["size"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 2
