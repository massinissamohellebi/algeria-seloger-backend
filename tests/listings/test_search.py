"""Full-text search (`q`) on GET /listings.

The suite runs on SQLite, so these exercise the dialect-aware fallback
(`lower(title || ' ' || description) LIKE :pattern`). The PostgreSQL
`websearch_to_tsquery` path shares the same code path and parameter binding;
its real behaviour is validated against Postgres separately (migration round-trip).
"""

import pytest

from tests.listings.test_router import auth_headers, create_listing


async def _published(client, headers, **overrides) -> dict:
    listing = await create_listing(client, headers, **overrides)
    await client.post(f"/listings/{listing['id']}/publish", headers=headers)
    return listing


@pytest.mark.asyncio
async def test_q_matches_word_in_title(client):
    headers = await auth_headers(client)
    villa = await _published(client, headers, title="Belle villa avec piscine")
    await _published(client, headers, title="Studio en centre-ville")

    resp = await client.get("/listings", params={"q": "piscine"})
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert ids == [villa["id"]]


@pytest.mark.asyncio
async def test_q_matches_word_in_description(client):
    headers = await auth_headers(client)
    match = await _published(
        client, headers, title="Appartement F3", description="Proche de la plage et calme"
    )
    await _published(client, headers, title="Appartement F4", description="Vue sur la montagne")

    resp = await client.get("/listings", params={"q": "plage"})
    ids = [i["id"] for i in resp.json()["items"]]
    assert ids == [match["id"]]


@pytest.mark.asyncio
async def test_q_is_case_insensitive(client):
    headers = await auth_headers(client)
    match = await _published(client, headers, title="Grand Loft Lumineux")

    resp = await client.get("/listings", params={"q": "LOFT"})
    assert [i["id"] for i in resp.json()["items"]] == [match["id"]]


@pytest.mark.asyncio
async def test_q_excludes_non_matching(client):
    headers = await auth_headers(client)
    await _published(client, headers, title="Villa moderne")

    resp = await client.get("/listings", params={"q": "hangar"})
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_q_never_returns_unpublished(client):
    headers = await auth_headers(client)
    # Draft (not published) that would match the term.
    await create_listing(client, headers, title="Villa secrète non publiée")

    resp = await client.get("/listings", params={"q": "secrète"})
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_empty_q_returns_all_published(client):
    headers = await auth_headers(client)
    await _published(client, headers, title="Villa un")
    await _published(client, headers, title="Studio deux")

    for params in ({}, {"q": ""}, {"q": "   "}):
        resp = await client.get("/listings", params=params)
        assert resp.json()["total"] == 2, params


@pytest.mark.asyncio
async def test_q_combined_with_wilaya_filter(client):
    headers = await auth_headers(client)
    match = await _published(client, headers, title="Villa avec jardin", wilaya="Oran")
    # Same keyword, different wilaya -> excluded by the intersection.
    await _published(client, headers, title="Villa avec jardin", wilaya="Alger")
    # Same wilaya, no keyword match -> excluded by q.
    await _published(client, headers, title="Studio moderne", wilaya="Oran")

    resp = await client.get("/listings", params={"q": "jardin", "wilaya": "Oran"})
    ids = [i["id"] for i in resp.json()["items"]]
    assert ids == [match["id"]]


@pytest.mark.asyncio
async def test_malicious_q_does_not_error(client):
    headers = await auth_headers(client)
    await _published(client, headers, title="Appartement standard")

    # SQL-injection and tsquery-operator payloads must be treated as a literal,
    # parameterised search term: no 500, no side effect on the table. (These
    # concrete strings do not match "Appartement standard", hence total == 0.)
    for payload in ("'; DROP TABLE listings; --", "a & b | !(", "\\' OR 1=1 --", "شقة"):
        resp = await client.get("/listings", params={"q": payload})
        assert resp.status_code == 200, payload
        assert resp.json()["total"] == 0, payload

    # A wildcard-only payload is harmless too (no error); on the SQLite fallback
    # LIKE it may match, so we only assert it does not blow up.
    assert (await client.get("/listings", params={"q": "%%%"})).status_code == 200

    # The table survived every injection attempt and is still queryable.
    assert (await client.get("/listings")).json()["total"] == 1
