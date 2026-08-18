import pytest

from tests._mailer import capturing_mailer


def listing_payload(**overrides) -> dict:
    payload = {
        "title": "Appartement F4 vue mer à Hydra",
        "description": "Lumineux et spacieux.",
        "transaction_type": "vente",
        "property_type": "appartement",
        "price": 45_000_000,
        "price_unit": "DZD_total",
        "surface": 120,
        "rooms": 4,
        "bedrooms": 3,
        "furnished": True,
        "amenities": ["Parking", "Balcon"],
        "wilaya": "Alger",
        "city": "Hydra",
    }
    payload.update(overrides)
    return payload


async def auth_headers(client, email: str = "owner@example.com") -> dict:
    creds = {"email": email, "password": "supersecret123", "full_name": "Owner"}
    await client.post("/auth/register", json=creds)
    # Login now requires a verified email: confirm it via the captured token.
    verify_token = capturing_mailer.token_for(email)
    await client.post("/auth/verify-email", json={"token": verify_token})
    login = await client.post("/auth/login", json={"email": email, "password": creds["password"]})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def create_listing(client, headers, **overrides) -> dict:
    resp = await client.post("/listings", json=listing_payload(**overrides), headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_requires_auth(client):
    resp = await client.post("/listings", json=listing_payload())
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_returns_201_draft(client):
    headers = await auth_headers(client)
    resp = await client.post("/listings", json=listing_payload(), headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "draft"
    assert body["owner_id"]
    assert body["price"] == 45_000_000
    assert body["amenities"] == ["Parking", "Balcon"]


@pytest.mark.asyncio
async def test_create_rejects_invalid_price(client):
    headers = await auth_headers(client)
    resp = await client.post("/listings", json=listing_payload(price=0), headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_returns_only_published(client):
    headers = await auth_headers(client)
    draft = await create_listing(client, headers)

    empty = await client.get("/listings")
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    await client.post(f"/listings/{draft['id']}/publish", headers=headers)
    published = await client.get("/listings")
    assert published.json()["total"] == 1
    assert published.json()["items"][0]["id"] == draft["id"]


@pytest.mark.asyncio
async def test_get_detail_visibility(client):
    owner = await auth_headers(client, "owner@example.com")
    other = await auth_headers(client, "other@example.com")
    draft = await create_listing(client, owner)

    # anonymous cannot see a draft
    assert (await client.get(f"/listings/{draft['id']}")).status_code == 404
    # another user cannot see it either
    assert (await client.get(f"/listings/{draft['id']}", headers=other)).status_code == 404
    # owner can see their own draft
    assert (await client.get(f"/listings/{draft['id']}", headers=owner)).status_code == 200

    await client.post(f"/listings/{draft['id']}/publish", headers=owner)
    # once published, anyone can see it
    assert (await client.get(f"/listings/{draft['id']}")).status_code == 200


@pytest.mark.asyncio
async def test_update_and_delete_ownership(client):
    owner = await auth_headers(client, "owner@example.com")
    other = await auth_headers(client, "other@example.com")
    listing = await create_listing(client, owner)

    ok = await client.patch(f"/listings/{listing['id']}", json={"price": 40_000_000}, headers=owner)
    assert ok.status_code == 200
    assert ok.json()["price"] == 40_000_000

    forbidden = await client.patch(f"/listings/{listing['id']}", json={"price": 1}, headers=other)
    assert forbidden.status_code == 403

    assert (await client.delete(f"/listings/{listing['id']}", headers=other)).status_code == 403
    assert (await client.delete(f"/listings/{listing['id']}", headers=owner)).status_code == 204
    assert (await client.get(f"/listings/{listing['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_publish_invalid_transition_returns_409(client):
    headers = await auth_headers(client)
    listing = await create_listing(client, headers)
    first = await client.post(f"/listings/{listing['id']}/publish", headers=headers)
    assert first.status_code == 200
    second = await client.post(f"/listings/{listing['id']}/publish", headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "invalid_status_transition"


@pytest.mark.asyncio
async def test_filters_and_sort(client):
    headers = await auth_headers(client)
    a = await create_listing(
        client, headers, title="Cheap Oran flat", price=20_000_000, wilaya="Oran"
    )
    b = await create_listing(
        client,
        headers,
        title="Pricey Alger villa",
        price=80_000_000,
        property_type="villa",
        wilaya="Alger",
    )
    for lid in (a["id"], b["id"]):
        await client.post(f"/listings/{lid}/publish", headers=headers)

    by_wilaya = await client.get("/listings", params={"wilaya": "Oran"})
    assert [i["id"] for i in by_wilaya.json()["items"]] == [a["id"]]

    by_price = await client.get("/listings", params={"price_max": 30_000_000})
    assert [i["id"] for i in by_price.json()["items"]] == [a["id"]]

    by_type = await client.get("/listings", params={"property_type": "villa"})
    assert [i["id"] for i in by_type.json()["items"]] == [b["id"]]

    asc = await client.get("/listings", params={"sort": "price_asc"})
    assert [i["id"] for i in asc.json()["items"]] == [a["id"], b["id"]]


@pytest.mark.asyncio
async def test_pagination(client):
    headers = await auth_headers(client)
    for n in range(3):
        listing = await create_listing(client, headers, title=f"Flat {n}")
        await client.post(f"/listings/{listing['id']}/publish", headers=headers)

    page1 = await client.get("/listings", params={"size": 2, "page": 1})
    assert page1.json()["total"] == 3
    assert page1.json()["pages"] == 2
    assert len(page1.json()["items"]) == 2

    page2 = await client.get("/listings", params={"size": 2, "page": 2})
    assert len(page2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_contact_fields_round_trip(client):
    headers = await auth_headers(client)
    body = await create_listing(
        client,
        headers,
        contact_name="Mohamed Cherif",
        contact_phone="+213555123456",
    )
    assert body["contact_name"] == "Mohamed Cherif"
    assert body["contact_phone"] == "+213555123456"

    detail = await client.get(f"/listings/{body['id']}", headers=headers)
    assert detail.json()["contact_phone"] == "+213555123456"


@pytest.mark.asyncio
async def test_list_mine_includes_drafts(client):
    owner = await auth_headers(client, "owner@example.com")
    other = await auth_headers(client, "other@example.com")
    await create_listing(client, owner, title="My draft")
    await create_listing(client, other, title="Their draft")

    mine = await client.get("/listings/mine", headers=owner)
    assert mine.status_code == 200
    assert [i["title"] for i in mine.json()] == ["My draft"]
