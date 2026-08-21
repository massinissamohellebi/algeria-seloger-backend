from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.service import AdminService
from app.core.database import get_db


def get_admin_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminService:
    return AdminService(session)
