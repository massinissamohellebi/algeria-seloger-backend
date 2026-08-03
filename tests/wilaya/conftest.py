from decimal import Decimal

import pytest_asyncio

from app.wilaya.models import Wilaya

# Mirror of the Alembic seed (subset of columns exercised by the tests). The test
# suite runs on SQLite via ``Base.metadata.create_all`` and never applies Alembic
# migrations, so we seed the reference rows explicitly here.
_SEED: list[tuple[str, str, str, str, float, float]] = [
    (f"{n:02d}", f"Wilaya {n}", f"ولاية {n}", f"Wilaya {n}", 30.0 + n * 0.1, 0.0 + n * 0.1)
    for n in range(1, 59)
]
# Pin a couple of well-known rows for meaningful assertions.
_SEED[15] = ("16", "Alger", "الجزائر", "Algiers", 36.753800, 3.058800)
_SEED[30] = ("31", "Oran", "وهران", "Oran", 35.696900, -0.633100)


@pytest_asyncio.fixture
async def seeded_wilayas(db_session):
    """Insert the 58 wilayas into the test DB (mirrors the Alembic seed)."""
    db_session.add_all(
        Wilaya(
            code=code,
            name_fr=name_fr,
            name_ar=name_ar,
            name_en=name_en,
            latitude=Decimal(str(latitude)),
            longitude=Decimal(str(longitude)),
        )
        for code, name_fr, name_ar, name_en, latitude, longitude in _SEED
    )
    await db_session.commit()
    return _SEED
