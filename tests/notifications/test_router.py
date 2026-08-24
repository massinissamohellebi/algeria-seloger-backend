"""Tests for the notifications API (epic vacances)."""

import pytest

from tests.listings.test_router import auth_headers
from tests.reservations.test_router import reserve_payload, vacation_listing


async def _make_notification(client):
    """Trigger a host notification via a new reservation request."""
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await vacation_listing(client, owner)
    await client.post(f"/listings/{lid}/reservations", json=reserve_payload(), headers=guest)
    return owner, guest


@pytest.mark.asyncio
async def test_requires_auth(client):
    assert (await client.get("/notifications")).status_code == 401


@pytest.mark.asyncio
async def test_list_and_unread_count(client):
    owner, guest = await _make_notification(client)
    resp = await client.get("/notifications", headers=owner)
    assert resp.status_code == 200
    body = resp.json()
    assert body["unread_count"] == 1
    assert len(body["items"]) == 1

    # The guest has no notification from their own request.
    assert (await client.get("/notifications", headers=guest)).json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mark_one_read(client):
    owner, _ = await _make_notification(client)
    nid = (await client.get("/notifications", headers=owner)).json()["items"][0]["id"]
    resp = await client.post(f"/notifications/{nid}/read", headers=owner)
    assert resp.status_code == 204
    assert (await client.get("/notifications/unread-count", headers=owner)).json()[
        "unread_count"
    ] == 0


@pytest.mark.asyncio
async def test_cannot_read_others_notification(client):
    owner, guest = await _make_notification(client)
    nid = (await client.get("/notifications", headers=owner)).json()["items"][0]["id"]
    resp = await client.post(f"/notifications/{nid}/read", headers=guest)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mark_all_read(client):
    owner, _ = await _make_notification(client)
    resp = await client.post("/notifications/read-all", headers=owner)
    assert resp.status_code == 204
    assert (await client.get("/notifications/unread-count", headers=owner)).json()[
        "unread_count"
    ] == 0
