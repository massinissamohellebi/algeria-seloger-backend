"""Tests for the reviews API (epic vacances)."""

import pytest

from tests.listings.test_router import auth_headers, create_listing


async def published_listing(client, owner_headers) -> str:
    listing = await create_listing(client, owner_headers)
    await client.post(f"/listings/{listing['id']}/publish", headers=owner_headers)
    return listing["id"]


@pytest.mark.asyncio
async def test_empty_aggregate_for_new_listing(client):
    owner = await auth_headers(client, "owner@example.com")
    lid = await published_listing(client, owner)
    resp = await client.get(f"/listings/{lid}/reviews")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["count"] == 0
    assert body["average"] is None
    assert body["coup_de_coeur"] is False


@pytest.mark.asyncio
async def test_owner_cannot_review_own_listing(client):
    owner = await auth_headers(client, "owner@example.com")
    lid = await published_listing(client, owner)
    resp = await client.post(f"/listings/{lid}/reviews", json={"rating": 5}, headers=owner)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "self_review_forbidden"


@pytest.mark.asyncio
async def test_guest_review_updates_aggregate(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await published_listing(client, owner)

    resp = await client.post(
        f"/listings/{lid}/reviews",
        json={"rating": 4, "comment": "Superbe séjour"},
        headers=guest,
    )
    assert resp.status_code == 201
    assert resp.json()["author_name"] == "Owner"
    assert resp.json()["rating"] == 4

    listed = await client.get(f"/listings/{lid}/reviews")
    body = listed.json()
    assert body["count"] == 1
    assert body["average"] == 4.0
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_second_review_by_same_user_is_upsert(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await published_listing(client, owner)

    await client.post(f"/listings/{lid}/reviews", json={"rating": 2}, headers=guest)
    await client.post(f"/listings/{lid}/reviews", json={"rating": 5}, headers=guest)

    body = (await client.get(f"/listings/{lid}/reviews")).json()
    assert body["count"] == 1
    assert body["average"] == 5.0


@pytest.mark.asyncio
async def test_coup_de_coeur_badge(client):
    owner = await auth_headers(client, "owner@example.com")
    lid = await published_listing(client, owner)
    for i in range(5):
        guest = await auth_headers(client, f"guest{i}@example.com")
        await client.post(f"/listings/{lid}/reviews", json={"rating": 5}, headers=guest)

    body = (await client.get(f"/listings/{lid}/reviews")).json()
    assert body["count"] == 5
    assert body["average"] == 5.0
    assert body["coup_de_coeur"] is True


@pytest.mark.asyncio
async def test_listing_detail_exposes_rating(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await published_listing(client, owner)
    await client.post(f"/listings/{lid}/reviews", json={"rating": 5}, headers=guest)

    detail = await client.get(f"/listings/{lid}")
    assert detail.json()["rating_avg"] == 5.0
    assert detail.json()["review_count"] == 1
