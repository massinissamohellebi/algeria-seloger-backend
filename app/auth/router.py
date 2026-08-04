from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_auth_service
from app.auth.schemas import (
    LoginRequest,
    PasswordChange,
    Token,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.auth.service import AuthService
from app.core.database import get_db

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[AuthService, Depends(get_auth_service)]

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRead:
    user = await service.register(payload)
    await session.commit()
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Token:
    return await service.login(payload.email, payload.password)


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> UserRead:
    user = await service.update_profile(current_user, payload)
    await session.commit()
    return UserRead.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> None:
    await service.change_password(
        current_user, payload.current_password, payload.new_password
    )
    await session.commit()


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> None:
    await service.delete_account(current_user)
    await session.commit()
