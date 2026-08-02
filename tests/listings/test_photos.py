import pytest

from app.core.config import settings
from app.core.storage import InMemoryStorage, get_storage
from app.main import app
from tests.listings.test_router import auth_headers, create_listing

JPEG = ("photo.jpg", b"\xff\xd8\xff" + b"0" * 128, "image/jpeg")


@pytest.fixture
def storage_backend():
    backend = InMemoryStorage()
    app.dependency_overrides[get_storage] = lambda: backend
    yield backend
    app.dependency_overrides.pop(get_storage, None)


async def upload(client, listing_id, headers, file=JPEG):
    return await client.post(
        f"/listings/{listing_id}/photos", files={"file": file}, headers=headers
    )


@pytest.mark.asyncio
async def test_upload_first_photo_is_cover(client, storage_backend):
    headers = await auth_headers(client)
    listing = await create_listing(client, headers)

    resp = await upload(client, listing["id"], headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_cover"] is True
    assert body["position"] == 0
    assert len(storage_backend.objects) == 1


@pytest.mark.asyncio
async def test_second_photo_not_cover(client, storage_backend):
    headers = await auth_headers(client)
    listing = await create_listing(client, headers)
    await upload(client, listing["id"], headers)
    second = await upload(
        client, listing["id"], headers, file=("2.png", b"\x89PNG" + b"0" * 64, "image/png")
    )
    assert second.json()["is_cover"] is False
    assert second.json()["position"] == 1


@pytest.mark.asyncio
async def test_upload_rejects_non_image(client, storage_backend):
    headers = await auth_headers(client)
    listing = await create_listing(client, headers)
    resp = await upload(client, listing["id"], headers, file=("note.txt", b"hello", "text/plain"))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_photo"
    assert storage_backend.objects == {}


@pytest.mark.asyncio
async def test_upload_rejects_oversized(client, storage_backend, monkeypatch):
    monkeypatch.setattr(settings, "max_photo_size_bytes", 10)
    headers = await auth_headers(client)
    listing = await create_listing(client, headers)
    resp = await upload(client, listing["id"], headers, file=("big.jpg", b"0" * 50, "image/jpeg"))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_enforces_max_photos(client, storage_backend, monkeypatch):
    monkeypatch.setattr(settings, "max_photos_per_listing", 2)
    headers = await auth_headers(client)
    listing = await create_listing(client, headers)
    assert (await upload(client, listing["id"], headers)).status_code == 201
    assert (await upload(client, listing["id"], headers)).status_code == 201
    third = await upload(client, listing["id"], headers)
    assert third.status_code == 409
    assert third.json()["error"]["code"] == "max_photos_reached"


@pytest.mark.asyncio
async def test_non_owner_cannot_upload_or_delete(client, storage_backend):
    owner = await auth_headers(client, "owner@example.com")
    other = await auth_headers(client, "other@example.com")
    listing = await create_listing(client, owner)
    photo = (await upload(client, listing["id"], owner)).json()

    assert (await upload(client, listing["id"], other)).status_code == 403
    delete = await client.delete(f"/listings/{listing['id']}/photos/{photo['id']}", headers=other)
    assert delete.status_code == 403


@pytest.mark.asyncio
async def test_delete_resequences_and_reassigns_cover(client, storage_backend):
    headers = await auth_headers(client)
    listing = await create_listing(client, headers)
    p1 = (await upload(client, listing["id"], headers)).json()
    await upload(
        client, listing["id"], headers, file=("2.png", b"\x89PNG" + b"0" * 64, "image/png")
    )

    # delete the cover (first photo)
    resp = await client.delete(f"/listings/{listing['id']}/photos/{p1['id']}", headers=headers)
    assert resp.status_code == 204
    assert len(storage_backend.objects) == 1

    await client.post(f"/listings/{listing['id']}/publish", headers=headers)
    detail = (await client.get(f"/listings/{listing['id']}")).json()
    assert len(detail["photos"]) == 1
    assert detail["photos"][0]["is_cover"] is True
    assert detail["photos"][0]["position"] == 0


@pytest.mark.asyncio
async def test_delete_missing_photo_returns_404(client, storage_backend):
    import uuid

    headers = await auth_headers(client)
    listing = await create_listing(client, headers)
    resp = await client.delete(f"/listings/{listing['id']}/photos/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404
