"""Tests for the admin analytics endpoint (Story 6)."""

import pytest

from tests.listings.test_admin import admin_headers
from tests.listings.test_router import auth_headers, create_listing


@pytest.mark.asyncio
async def test_analytics_requires_admin(client):
    non_admin = await auth_headers(client, "user@example.com")
    assert (await client.get("/admin/analytics")).status_code == 401
    assert (await client.get("/admin/analytics", headers=non_admin)).status_code == 403


@pytest.mark.asyncio
async def test_analytics_returns_kpis(client, db_session):
    owner = await auth_headers(client, "owner@example.com")
    admin = await admin_headers(client, db_session)
    listing = await create_listing(client, owner)
    await client.post("/reports", json={"reason": "fraud", "listing_id": listing["id"]})

    resp = await client.get("/admin/analytics", headers=admin)
    assert resp.status_code == 200
    body = resp.json()

    # Six KPI groups present + summary counters populated from real data.
    for key in (
        "dau",
        "mau",
        "total_users",
        "total_listings",
        "total_conversations",
        "listings_per_day",
        "conversations_per_day",
        "reports_per_day",
        "top_report_reasons",
        "top_wilayas",
    ):
        assert key in body

    assert body["total_listings"] >= 1
    assert body["total_conversations"] == 0
    assert any(r["label"] == "fraud" for r in body["top_report_reasons"])


@pytest.mark.asyncio
async def test_analytics_accepts_date_range(client, db_session):
    admin = await admin_headers(client, db_session)
    resp = await client.get(
        "/admin/analytics?from=2026-01-01&to=2026-01-31", headers=admin
    )
    assert resp.status_code == 200
    assert resp.json()["date_from"] == "2026-01-01"
    assert resp.json()["date_to"] == "2026-01-31"
