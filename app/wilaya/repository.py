from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.wilaya.models import Wilaya


class WilayaRepository:
    """Data-access layer for wilayas (no business logic)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Wilaya]:
        result = await self.session.execute(select(Wilaya).order_by(Wilaya.code.asc()))
        return list(result.scalars().all())
