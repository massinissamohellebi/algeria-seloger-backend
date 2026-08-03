"""S2 — structured filters on GET /listings (multi property_type, city,
surface range, rooms_min, amenities AND-contains) + combination with `q`.

Runs on SQLite, so the amenities clause exercises the dialect-aware
``json_each`` fallback; the PostgreSQL ``jsonb @>`` path shares the same
parameter-binding code and is validated against Postgres separately.
"""

import pytest

from tests.listings.test_router import auth_headers, create_listing


async def _published(client, headers, **overrides) -> dict:
    listing = await create_listing(client, headers, **overrides)
    await client.post(f"/listings/{listing['id']}/publish", headers=headers)
    return listing


def _ids(resp) -> list[str]:
    return [i["id"] for i in resp.json()["items"]]


@pytest.mark.asyncio
async def test_property_type_multi_is_or(client):
    headers = await auth_headers(client)
    appart = await _published(client, headers, title="Appart", property_type="appartement")
    villa = await _published(client, headers, title="Villa", property_type="villa")
    await _published(client, headers, title="Studio", property_type="studio")

    resp = await client.get("/listings", params={"property_type": ["appartement", "villa"]})
    assert resp.status_code == 200
    assert set(_ids(resp)) == {appart["id"], villa["id"]}


@pytest.mark.asyncio
async def test_property_type_single_still_works(client):
    headers = await auth_headers(client)
    villa = await _published(client, headers, title="Villa", property_type="villa")
    await _published(client, headers, title="Studio", property_type="studio")

    resp = await client.get("/listings", params={"property_type": "villa"})
    assert _ids(resp) == [villa["id"]]


@pytest.mark.asyncio
async def test_city_filter(client):
    headers = await auth_headers(client)
    hydra = await _published(client, headers, title="Bien Hydra", city="Hydra")
    await _published(client, headers, title="Bien Kouba", city="Kouba")

    resp = await client.get("/listings", params={"city": "Hydra"})
    assert _ids(resp) == [hydra["id"]]


@pytest.mark.asyncio
async def test_surface_range(client):
    headers = await auth_headers(client)
    small = await _published(client, headers, title="Small", surface=50)
    mid = await _published(client, headers, title="Mid", surface=100)
    await _published(client, headers, title="Big", surface=200)

    resp = await client.get("/listings", params={"surface_min": 60, "surface_max": 150})
    assert _ids(resp) == [mid["id"]]

    # min 60 keeps mid(100) and big(200), excludes small(50).
    only_min = await client.get("/listings", params={"surface_min": 60})
    assert small["id"] not in _ids(only_min)
    assert mid["id"] in _ids(only_min)


@pytest.mark.asyncio
async def test_rooms_min(client):
    headers = await auth_headers(client)
    await _published(client, headers, title="Petit F2", rooms=2)
    f4 = await _published(client, headers, title="Grand F4", rooms=4)

    resp = await client.get("/listings", params={"rooms_min": 3})
    assert _ids(resp) == [f4["id"]]


@pytest.mark.asyncio
async def test_amenities_and_contains(client):
    headers = await auth_headers(client)
    listing = await _published(
        client, headers, title="With parking+lift", amenities=["parking", "ascenseur"]
    )

    # Subset requested -> match.
    one = await client.get("/listings", params={"amenities": ["parking"]})
    assert _ids(one) == [listing["id"]]

    # Exact set requested -> match.
    both = await client.get("/listings", params={"amenities": ["parking", "ascenseur"]})
    assert _ids(both) == [listing["id"]]

    # Requesting an amenity it lacks -> excluded (AND semantics).
    missing = await client.get("/listings", params={"amenities": ["parking", "piscine"]})
    assert missing.json()["total"] == 0


@pytest.mark.asyncio
async def test_filters_combined_with_q(client):
    headers = await auth_headers(client)
    match = await _published(
        client,
        headers,
        title="Villa avec jardin",
        property_type="villa",
        city="Oran",
        surface=180,
        rooms=5,
        amenities=["parking", "jardin"],
    )
    # Wrong city.
    await _published(
        client, headers, title="Villa avec jardin", property_type="villa", city="Alger"
    )
    # No keyword match.
    await _published(client, headers, title="Studio moderne", property_type="villa", city="Oran")
    # Missing amenity.
    await _published(
        client,
        headers,
        title="Villa avec jardin",
        property_type="villa",
        city="Oran",
        amenities=["parking"],
    )

    resp = await client.get(
        "/listings",
        params={
            "q": "jardin",
            "property_type": ["villa", "maison"],
            "city": "Oran",
            "surface_min": 100,
            "rooms_min": 3,
            "amenities": ["parking", "jardin"],
        },
    )
    assert _ids(resp) == [match["id"]]


@pytest.mark.asyncio
async def test_date_desc_alias_accepted(client):
    headers = await auth_headers(client)
    await _published(client, headers, title="One")
    resp = await client.get("/listings", params={"sort": "date_desc"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"price_min": -1},
        {"surface_min": -5},
        {"rooms_min": -2},
        {"size": 5000},
        {"page": 0},
        {"property_type": "not_a_real_type"},
        {"sort": "bogus"},
    ],
)
async def test_invalid_params_return_422(client, params):
    resp = await client.get("/listings", params=params)
    assert resp.status_code == 422
