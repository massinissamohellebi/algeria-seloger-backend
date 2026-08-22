"""Tests for the messaging API (epic 05, stories C1–C3)."""

import uuid

import pytest

from tests.listings.test_router import auth_headers, create_listing


async def published_listing(client, owner_headers) -> str:
    listing = await create_listing(client, owner_headers)
    await client.post(f"/listings/{listing['id']}/publish", headers=owner_headers)
    return listing["id"]


async def setup_pair(client):
    owner = await auth_headers(client, "owner@example.com")
    enquirer = await auth_headers(client, "enquirer@example.com")
    lid = await published_listing(client, owner)
    return owner, enquirer, lid


# --- Start / resume (C2) ---------------------------------------------------


@pytest.mark.asyncio
async def test_start_requires_auth(client):
    resp = await client.post(
        "/conversations",
        json={"listing_id": str(uuid.uuid4()), "initial_message": "hi"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_start_unknown_listing_404(client):
    _, enquirer, _ = await setup_pair(client)
    resp = await client.post(
        "/conversations",
        json={"listing_id": str(uuid.uuid4()), "initial_message": "Bonjour"},
        headers=enquirer,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_contact_own_listing(client):
    owner, _, lid = await setup_pair(client)
    resp = await client.post(
        "/conversations",
        json={"listing_id": lid, "initial_message": "Bonjour"},
        headers=owner,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "self_contact_forbidden"


@pytest.mark.asyncio
async def test_start_then_resume_is_idempotent(client):
    _, enquirer, lid = await setup_pair(client)
    first = await client.post(
        "/conversations",
        json={"listing_id": lid, "initial_message": "Disponible ?"},
        headers=enquirer,
    )
    assert first.status_code == 201
    conv_id = first.json()["id"]

    second = await client.post(
        "/conversations",
        json={"listing_id": lid, "initial_message": "Toujours là ?"},
        headers=enquirer,
    )
    assert second.status_code == 200
    assert second.json()["id"] == conv_id

    # The resume added a second message.
    thread = await client.get(f"/conversations/{conv_id}/messages", headers=enquirer)
    assert thread.json()["total"] == 2


@pytest.mark.asyncio
async def test_start_empty_message_422(client):
    _, enquirer, lid = await setup_pair(client)
    resp = await client.post(
        "/conversations",
        json={"listing_id": lid, "initial_message": ""},
        headers=enquirer,
    )
    assert resp.status_code == 422


# --- List / thread / send / read / unread (C3) -----------------------------


@pytest.mark.asyncio
async def test_thread_forbidden_for_non_participant(client):
    _, enquirer, lid = await setup_pair(client)
    outsider = await auth_headers(client, "outsider@example.com")
    conv = await client.post(
        "/conversations",
        json={"listing_id": lid, "initial_message": "Hello"},
        headers=enquirer,
    )
    cid = conv.json()["id"]
    resp = await client.get(f"/conversations/{cid}/messages", headers=outsider)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_send_message_and_read_flow(client):
    owner, enquirer, lid = await setup_pair(client)
    conv = await client.post(
        "/conversations",
        json={"listing_id": lid, "initial_message": "Bonjour"},
        headers=enquirer,
    )
    cid = conv.json()["id"]

    # Owner has one unread; enquirer has none.
    assert (await client.get("/conversations/unread-count", headers=owner)).json()[
        "unread_count"
    ] == 1
    assert (await client.get("/conversations/unread-count", headers=enquirer)).json()[
        "unread_count"
    ] == 0

    # Owner opens the thread → messages marked read.
    thread = await client.get(f"/conversations/{cid}/messages", headers=owner)
    assert thread.status_code == 200
    assert (await client.get("/conversations/unread-count", headers=owner)).json()[
        "unread_count"
    ] == 0

    # Owner replies.
    reply = await client.post(
        f"/conversations/{cid}/messages",
        json={"body": "Oui, disponible"},
        headers=owner,
    )
    assert reply.status_code == 201
    # Now the enquirer has one unread.
    assert (await client.get("/conversations/unread-count", headers=enquirer)).json()[
        "unread_count"
    ] == 1


@pytest.mark.asyncio
async def test_message_body_validation(client):
    _, enquirer, lid = await setup_pair(client)
    conv = await client.post(
        "/conversations",
        json={"listing_id": lid, "initial_message": "Bonjour"},
        headers=enquirer,
    )
    cid = conv.json()["id"]
    empty = await client.post(
        f"/conversations/{cid}/messages", json={"body": ""}, headers=enquirer
    )
    assert empty.status_code == 422
    too_long = await client.post(
        f"/conversations/{cid}/messages",
        json={"body": "x" * 2001},
        headers=enquirer,
    )
    assert too_long.status_code == 422


@pytest.mark.asyncio
async def test_list_conversations_scoped_with_preview(client):
    owner, enquirer, lid = await setup_pair(client)
    await client.post(
        "/conversations",
        json={"listing_id": lid, "initial_message": "Bonjour"},
        headers=enquirer,
    )
    listed = await client.get("/conversations", headers=enquirer)
    assert listed.json()["total"] == 1
    item = listed.json()["items"][0]
    assert item["listing"]["id"] == lid
    assert item["last_message"]["body"] == "Bonjour"

    # An unrelated user sees none.
    outsider = await auth_headers(client, "outsider@example.com")
    assert (await client.get("/conversations", headers=outsider)).json()["total"] == 0


@pytest.mark.asyncio
async def test_by_listing_lookup(client):
    _, enquirer, lid = await setup_pair(client)
    missing = await client.get(f"/conversations/by-listing/{lid}", headers=enquirer)
    assert missing.status_code == 404

    conv = await client.post(
        "/conversations",
        json={"listing_id": lid, "initial_message": "Bonjour"},
        headers=enquirer,
    )
    found = await client.get(f"/conversations/by-listing/{lid}", headers=enquirer)
    assert found.status_code == 200
    assert found.json()["id"] == conv.json()["id"]
