import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import get_admin_service
from app.admin.schemas import (
    AdminUserPage,
    AdminUserRead,
    AnalyticsResponse,
    SuspendRequest,
)
from app.admin.service import AdminService
from app.auth.dependencies import AdminUser
from app.auth.models import UserStatus
from app.core.database import get_db

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[AdminService, Depends(get_admin_service)]

router = APIRouter(prefix="/admin", tags=["admin"])


# --- User management (Story 4) ---------------------------------------------


@router.get("/users", response_model=AdminUserPage)
async def list_users(
    _admin: AdminUser,
    service: ServiceDep,
    search: Annotated[str | None, Query(max_length=200)] = None,
    status: UserStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminUserPage:
    return await service.list_users(
        search=search, status=status, page=page, size=size
    )


@router.post("/users/{user_id}/suspend", response_model=AdminUserRead)
async def suspend_user(
    user_id: uuid.UUID,
    payload: SuspendRequest,
    admin: AdminUser,
    session: SessionDep,
    service: ServiceDep,
) -> AdminUserRead:
    user = await service.suspend(admin, user_id, payload.suspended_until)
    await session.commit()
    return AdminUserRead.model_validate(user)


@router.post("/users/{user_id}/ban", response_model=AdminUserRead)
async def ban_user(
    user_id: uuid.UUID,
    admin: AdminUser,
    session: SessionDep,
    service: ServiceDep,
) -> AdminUserRead:
    user = await service.ban(admin, user_id)
    await session.commit()
    return AdminUserRead.model_validate(user)


@router.post("/users/{user_id}/reactivate", response_model=AdminUserRead)
async def reactivate_user(
    user_id: uuid.UUID,
    admin: AdminUser,
    session: SessionDep,
    service: ServiceDep,
) -> AdminUserRead:
    user = await service.reactivate(admin, user_id)
    await session.commit()
    return AdminUserRead.model_validate(user)


# --- Analytics (Story 6) ----------------------------------------------------


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics(
    _admin: AdminUser,
    service: ServiceDep,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> AnalyticsResponse:
    to_value = date_to or date.today()
    from_value = date_from or (to_value - timedelta(days=29))
    return await service.get_analytics(from_value, to_value)
