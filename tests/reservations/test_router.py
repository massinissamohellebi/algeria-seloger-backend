"""Tests for the reservations API (epic vacances)."""

import uuid

import pytest

from tests._mailer import capturing_mailer
from tests.listings.test_router import auth_headers, create_listing


async def vacation_listing(client, owner_headers, max_guests: int = 2) -> str:
    listing = await create_listing(
        client,
        owner_headers,
        transaction_type="vacances",
        price_unit="DZD_night",
        price=8000,
        max_guests=max_guests,
        beds=1,
        pets_allowed=False,
        checkin_from="14:00",
        checkin_to="20:00",
        checkout_before="11:00",
    )
    await client.post(f"/listings/{listing['id']}/publish", headers=owner_headers)
    return listing["id"]


def reserve_payload(check_in="2026-09-01", check_out="2026-09-05", guests=2) -> dict:
    return {"check_in": check_in, "check_out": check_out, "guests": guests}


def _emails_to(email: str, needle: str) -> list[dict]:
    return [m for m in capturing_mailer.sent if m["to"] == email and needle in m["subject"]]


@pytest.mark.asyncio
async def test_create_requires_auth(client):
    resp = await client.post(f"/listings/{uuid.uuid4()}/reservations", json=reserve_payload())
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cannot_reserve_own_listing(client):
    owner = await auth_headers(client, "owner@example.com")
    lid = await vacation_listing(client, owner)
    resp = await client.post(f"/listings/{lid}/reservations", json=reserve_payload(), headers=owner)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "self_reservation_forbidden"


@pytest.mark.asyncio
async def test_cannot_reserve_non_vacation_listing(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    listing = await create_listing(client, owner)
    await client.post(f"/listings/{listing['id']}/publish", headers=owner)
    resp = await client.post(
        f"/listings/{listing['id']}/reservations",
        json=reserve_payload(),
        headers=guest,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "not_vacation_listing"


@pytest.mark.asyncio
async def test_invalid_date_range(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await vacation_listing(client, owner)
    resp = await client.post(
        f"/listings/{lid}/reservations",
        json=reserve_payload(check_in="2026-09-05", check_out="2026-09-01"),
        headers=guest,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_date_range"


@pytest.mark.asyncio
async def test_too_many_guests(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await vacation_listing(client, owner, max_guests=2)
    resp = await client.post(
        f"/listings/{lid}/reservations",
        json=reserve_payload(guests=5),
        headers=guest,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "too_many_guests"


@pytest.mark.asyncio
async def test_create_lists_and_notifies_host(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await vacation_listing(client, owner)

    resp = await client.post(f"/listings/{lid}/reservations", json=reserve_payload(), headers=guest)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["listing"]["id"] == lid

    # Guest and host see it from their respective endpoints.
    assert (await client.get("/reservations/guest", headers=guest)).json()["total"] == 1
    assert (await client.get("/reservations/host", headers=owner)).json()["total"] == 1

    # The host received an in-app notification.
    notifs = (await client.get("/notifications", headers=owner)).json()
    assert notifs["unread_count"] == 1
    assert notifs["items"][0]["link"] == "/profil/reservations"


@pytest.mark.asyncio
async def test_confirm_cancels_overlapping_and_emails(client):
    owner = await auth_headers(client, "owner@example.com")
    g1 = await auth_headers(client, "guest1@example.com")
    g2 = await auth_headers(client, "guest2@example.com")
    lid = await vacation_listing(client, owner)

    r1 = await client.post(
        f"/listings/{lid}/reservations",
        json=reserve_payload("2026-09-01", "2026-09-05"),
        headers=g1,
    )
    await client.post(
        f"/listings/{lid}/reservations",
        json=reserve_payload("2026-09-03", "2026-09-07"),
        headers=g2,
    )
    rid1 = r1.json()["id"]

    confirm = await client.post(f"/reservations/{rid1}/confirm", headers=owner)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"

    # Guest 1 confirmed by email; guest 2 auto-cancelled by email.
    assert _emails_to("guest1@example.com", "confirmée")
    assert _emails_to("guest2@example.com", "annulée")

    # Guest 2's reservation is now cancelled.
    g2_list = (await client.get("/reservations/guest", headers=g2)).json()
    assert g2_list["items"][0]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_confirm_requires_host(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await vacation_listing(client, owner)
    r = await client.post(f"/listings/{lid}/reservations", json=reserve_payload(), headers=guest)
    rid = r.json()["id"]
    resp = await client.post(f"/reservations/{rid}/confirm", headers=guest)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "not_reservation_host"


@pytest.mark.asyncio
async def test_confirm_twice_not_actionable(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await vacation_listing(client, owner)
    r = await client.post(f"/listings/{lid}/reservations", json=reserve_payload(), headers=guest)
    rid = r.json()["id"]
    await client.post(f"/reservations/{rid}/confirm", headers=owner)
    again = await client.post(f"/reservations/{rid}/confirm", headers=owner)
    assert again.status_code == 400
    assert again.json()["error"]["code"] == "reservation_not_actionable"


@pytest.mark.asyncio
async def test_host_manual_cancel_emails_guest(client):
    owner = await auth_headers(client, "owner@example.com")
    guest = await auth_headers(client, "guest@example.com")
    lid = await vacation_listing(client, owner)
    r = await client.post(f"/listings/{lid}/reservations", json=reserve_payload(), headers=guest)
    rid = r.json()["id"]
    resp = await client.post(f"/reservations/{rid}/cancel", headers=owner)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    assert _emails_to("guest@example.com", "annulée")
