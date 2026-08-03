import pytest

_FIELDS = {"code", "name_fr", "name_ar", "name_en", "latitude", "longitude"}


@pytest.mark.asyncio
async def test_list_wilayas_returns_200_with_58_items(client, seeded_wilayas):
    resp = await client.get("/wilayas")

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 58


@pytest.mark.asyncio
async def test_list_wilayas_is_public(client, seeded_wilayas):
    # No Authorization header — the endpoint must not require auth.
    resp = await client.get("/wilayas")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_wilayas_sorted_by_code_with_all_fields(client, seeded_wilayas):
    resp = await client.get("/wilayas")
    body = resp.json()

    codes = [item["code"] for item in body]
    assert codes == sorted(codes)
    assert codes[0] == "01"

    for item in body:
        assert _FIELDS.issubset(item.keys())


@pytest.mark.asyncio
async def test_list_wilayas_sample_alger(client, seeded_wilayas):
    resp = await client.get("/wilayas")
    body = {item["code"]: item for item in resp.json()}

    alger = body["16"]
    assert alger["name_fr"] == "Alger"
    assert alger["name_ar"]  # arabic name present
    assert alger["name_en"] == "Algiers"
    assert float(alger["latitude"]) == pytest.approx(36.7538, abs=1e-3)
