import pytest

from app.wilaya.repository import WilayaRepository


@pytest.mark.asyncio
async def test_list_all_returns_58_sorted_by_code(db_session, seeded_wilayas):
    repo = WilayaRepository(db_session)
    wilayas = await repo.list_all()

    assert len(wilayas) == 58
    codes = [w.code for w in wilayas]
    assert codes == sorted(codes)
    assert codes[0] == "01"
    assert codes[-1] == "58"


@pytest.mark.asyncio
async def test_list_all_empty_returns_empty_list(db_session):
    repo = WilayaRepository(db_session)
    assert await repo.list_all() == []
