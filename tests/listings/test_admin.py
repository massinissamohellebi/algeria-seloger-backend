import pytest
from sqlalchemy import select

from app.auth.models import User
from tests.listings.test_router import auth_headers, create_listing


async def admin_headers(client, db_session, email: str = "admin@example.com") -> dict:
    headers = await auth_headers(client, email)
    user = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
    user.is_admin = True
    await db_session.commit()
    return headers


async def published_listing(client, owner_headers) -> dict:
    listing = await create_listing(client, owner_headers)
    await client.post(f"/listings/{listing['id']}/publish", headers=owner_headers)
    return listing


@pytest.mark.asyncio
async def test_set_status_requires_auth(client):
    resp = await client.post(
        "/admin/listings/00000000-0000-0000-0000-000000000000/status",
        json={"status": "moderated"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_set_status_forbidden_for_non_admin(client):
    owner = await auth_headers(client, "owner@example.com")
    listing = await published_listing(client, owner)
    resp = await client.post(
        f"/admin/listings/{listing['id']}/status",
        json={"status": "moderated"},
        headers=owner,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_moderate_and_hidden_from_public(client, db_session):
    owner = await auth_headers(client, "owner@example.com")
    admin = await admin_headers(client, db_session)
    listing = await published_listing(client, owner)

    assert (await client.get("/listings")).json()["total"] == 1

    resp = await client.post(
        f"/admin/listings/{listing['id']}/status",
        json={"status": "moderated"},
        headers=admin,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "moderated"

    # moderated listing disappears from public results and detail
    assert (await client.get("/listings")).json()["total"] == 0
    assert (await client.get(f"/listings/{listing['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_admin_can_restore_listing(client, db_session):
    owner = await auth_headers(client, "owner@example.com")
    admin = await admin_headers(client, db_session)
    listing = await published_listing(client, owner)

    await client.post(
        f"/admin/listings/{listing['id']}/status",
        json={"status": "moderated"},
        headers=admin,
    )
    restore = await client.post(
        f"/admin/listings/{listing['id']}/status",
        json={"status": "published"},
        headers=admin,
    )
    assert restore.status_code == 200
    assert (await client.get("/listings")).json()["total"] == 1


@pytest.mark.asyncio
async def test_admin_list_returns_all_statuses(client, db_session):
    owner = await auth_headers(client, "owner@example.com")
    admin = await admin_headers(client, db_session)
    await create_listing(client, owner, title="A draft")
    await published_listing(client, owner)

    all_listings = await client.get("/admin/listings", headers=admin)
    assert all_listings.status_code == 200
    assert all_listings.json()["total"] == 2

    drafts = await client.get("/admin/listings", params={"status": "draft"}, headers=admin)
    assert drafts.json()["total"] == 1
    assert drafts.json()["items"][0]["title"] == "A draft"


@pytest.mark.asyncio
async def test_admin_list_forbidden_for_non_admin(client):
    owner = await auth_headers(client, "owner@example.com")
    assert (await client.get("/admin/listings", headers=owner)).status_code == 403
