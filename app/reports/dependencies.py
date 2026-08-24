from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.reports.service import ReportService


def get_report_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReportService:
    return ReportService(session)
