import pytest

from app.wilaya.repository import WilayaRepository
from app.wilaya.schemas import WilayaRead
from app.wilaya.service import WilayaService


@pytest.mark.asyncio
async def test_list_wilayas_returns_58_read_schemas_sorted(db_session, seeded_wilayas):
    service = WilayaService(WilayaRepository(db_session))
    wilayas = await service.list_wilayas()

    assert len(wilayas) == 58
    assert all(isinstance(w, WilayaRead) for w in wilayas)
    codes = [w.code for w in wilayas]
    assert codes == sorted(codes)

    alger = next(w for w in wilayas if w.code == "16")
    assert alger.name_fr == "Alger"
    assert alger.name_ar == "الجزائر"
