import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AdminUser, OptionalCurrentUser
from app.core.database import get_db
from app.reports.dependencies import get_report_service
from app.reports.models import ReportReason, ReportStatus
from app.reports.schemas import (
    AdminReportPage,
    ReportCreate,
    ReportRead,
    ReportUpdate,
)
from app.reports.service import ReportService

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[ReportService, Depends(get_report_service)]

router = APIRouter(prefix="/reports", tags=["reports"])
admin_router = APIRouter(prefix="/admin/reports", tags=["admin"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreate,
    request: Request,
    current_user: OptionalCurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> ReportRead:
    report = await service.create_report(
        current_user, payload, ip=_client_ip(request)
    )
    await session.commit()
    return ReportRead.model_validate(report)


@admin_router.get("", response_model=AdminReportPage)
async def list_reports(
    _admin: AdminUser,
    service: ServiceDep,
    report_status: Annotated[ReportStatus | None, Query(alias="status")] = None,
    reason: ReportReason | None = None,
    target_type: Annotated[str | None, Query(pattern="^(listing|user)$")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminReportPage:
    return await service.list_reports(
        status=report_status,
        reason=reason,
        target_type=target_type,
        page=page,
        size=size,
    )


@admin_router.patch("/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: uuid.UUID,
    payload: ReportUpdate,
    admin: AdminUser,
    session: SessionDep,
    service: ServiceDep,
) -> ReportRead:
    report = await service.update_report(
        report_id, admin, payload.status, payload.admin_note
    )
    await session.commit()
    return ReportRead.model_validate(report)
