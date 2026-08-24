"""Tests for report creation (Story 2) + admin report queue (Story 3)."""

import uuid

import pytest
from sqlalchemy import select

from app.auth.models import User
from tests.listings.test_admin import admin_headers
from tests.listings.test_router import auth_headers, create_listing


async def make_listing(client, headers) -> str:
    listing = await create_listing(client, headers)
    return listing["id"]


async def user_id(db_session, email: str) -> str:
    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    return str(user.id)


# --- Create (Story 2) ------------------------------------------------------


@pytest.mark.asyncio
async def test_anonymous_report_on_listing(client):
    owner = await auth_headers(client, "owner@example.com")
    lid = await make_listing(client, owner)

    resp = await client.post(
        "/reports", json={"reason": "fraud", "listing_id": lid, "message": "arnaque"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "open"
    assert body["reporter_id"] is None


@pytest.mark.asyncio
async def test_authenticated_report_records_reporter(client):
    owner = await auth_headers(client, "owner@example.com")
    reporter = await auth_headers(client, "reporter@example.com")
    lid = await make_listing(client, owner)

    resp = await client.post(
        "/reports", json={"reason": "spam", "listing_id": lid}, headers=reporter
    )
    assert resp.status_code == 201
    assert resp.json()["reporter_id"] is not None


@pytest.mark.asyncio
async def test_report_requires_exactly_one_target(client, db_session):
    owner = await auth_headers(client, "owner@example.com")
    lid = await make_listing(client, owner)
    uid = await user_id(db_session, "owner@example.com")

    both = await client.post(
        "/reports",
        json={"reason": "spam", "listing_id": lid, "reported_user_id": uid},
    )
    assert both.status_code == 422
    neither = await client.post("/reports", json={"reason": "spam"})
    assert neither.status_code == 422


@pytest.mark.asyncio
async def test_report_nonexistent_target_returns_404(client):
    resp = await client.post(
        "/reports", json={"reason": "spam", "listing_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_report_creation_is_rate_limited(client):
    owner = await auth_headers(client, "owner@example.com")
    lid = await make_listing(client, owner)

    for _ in range(10):
        ok = await client.post("/reports", json={"reason": "spam", "listing_id": lid})
        assert ok.status_code == 201
    limited = await client.post("/reports", json={"reason": "spam", "listing_id": lid})
    assert limited.status_code == 429


# --- Admin queue (Story 3) -------------------------------------------------


@pytest.mark.asyncio
async def test_admin_reports_requires_admin(client):
    non_admin = await auth_headers(client, "user@example.com")
    assert (await client.get("/admin/reports")).status_code == 401
    assert (await client.get("/admin/reports", headers=non_admin)).status_code == 403


@pytest.mark.asyncio
async def test_admin_lists_reports_with_target_preview(client, db_session):
    owner = await auth_headers(client, "owner@example.com")
    admin = await admin_headers(client, db_session)
    lid = await make_listing(client, owner)
    await client.post("/reports", json={"reason": "fraud", "listing_id": lid})

    resp = await client.get("/admin/reports", headers=admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["target"]["type"] == "listing"
    assert item["target"]["id"] == lid
    assert item["target_report_count"] == 1


@pytest.mark.asyncio
async def test_admin_resolves_report(client, db_session):
    owner = await auth_headers(client, "owner@example.com")
    admin = await admin_headers(client, db_session)
    lid = await make_listing(client, owner)
    created = await client.post(
        "/reports", json={"reason": "fraud", "listing_id": lid}
    )
    report_id = created.json()["id"]

    resp = await client.patch(
        f"/admin/reports/{report_id}",
        json={"status": "resolved", "admin_note": "handled"},
        headers=admin,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
