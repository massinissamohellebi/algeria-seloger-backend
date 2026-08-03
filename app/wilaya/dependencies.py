from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.wilaya.repository import WilayaRepository
from app.wilaya.service import WilayaService


def get_wilaya_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WilayaService:
    return WilayaService(WilayaRepository(session))
