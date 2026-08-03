from app.wilaya.repository import WilayaRepository
from app.wilaya.schemas import WilayaRead


class WilayaService:
    """Business logic for wilaya reference data (read-only in V1)."""

    def __init__(self, repository: WilayaRepository) -> None:
        self.repository = repository

    async def list_wilayas(self) -> list[WilayaRead]:
        wilayas = await self.repository.list_all()
        return [WilayaRead.model_validate(wilaya) for wilaya in wilayas]
