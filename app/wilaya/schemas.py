from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class WilayaRead(BaseModel):
    """Public read shape for a wilaya (ADR-0005)."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name_fr: str
    name_ar: str
    name_en: str
    latitude: Decimal
    longitude: Decimal
