from decimal import Decimal

from sqlalchemy import CHAR, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Wilaya(Base):
    """An Algerian wilaya (administrative province).

    Read-only reference data seeded via an Alembic migration; the 58 wilayas
    are exposed by the public ``GET /wilayas`` endpoint (ADR-0005).
    """

    __tablename__ = "wilayas"

    code: Mapped[str] = mapped_column(CHAR(2), primary_key=True)  # '01'…'58'
    name_fr: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
