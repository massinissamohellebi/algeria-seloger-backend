from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.auth.schemas import UserRead
from app.core.database import get_db
from app.users.dependencies import get_profile_service
from app.users.schemas import (
    ChangePasswordRequest,
    PreferencesUpdate,
    ProfileUpdate,
)
from app.users.service import ProfileService

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[ProfileService, Depends(get_profile_service)]

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: ProfileUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> UserRead:
    user = await service.update_profile(current_user, payload)
    await session.commit()
    return UserRead.model_validate(user)


@router.patch("/me/preferences", response_model=UserRead)
async def update_preferences(
    payload: PreferencesUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> UserRead:
    user = await service.update_preferences(current_user, payload)
    await session.commit()
    return UserRead.model_validate(user)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> None:
    await service.change_password(
        current_user, payload.current_password, payload.new_password
    )
    await session.commit()


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
    file: Annotated[UploadFile, File()],
) -> UserRead:
    data = await file.read()
    user = await service.upload_avatar(
        current_user, data, file.content_type or ""
    )
    await session.commit()
    return UserRead.model_validate(user)


@router.delete("/me/avatar", response_model=UserRead)
async def remove_avatar(
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> UserRead:
    user = await service.remove_avatar(current_user)
    await session.commit()
    return UserRead.model_validate(user)


@router.get("/me/export")
async def export_me(
    current_user: CurrentUser,
    service: ServiceDep,
) -> dict:
    return await service.export_data(current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> None:
    await service.delete_account(current_user)
    await session.commit()
