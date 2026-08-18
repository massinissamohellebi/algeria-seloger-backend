from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_auth_service
from app.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordChange,
    RefreshRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserRead,
    UserUpdate,
    VerifyEmailRequest,
)
from app.auth.service import AuthService
from app.core.database import get_db
from app.core.exceptions import AppError

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[AuthService, Depends(get_auth_service)]

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: UserCreate,
    session: SessionDep,
    service: ServiceDep,
) -> UserRead:
    user = await service.register(payload)
    await session.commit()
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    request: Request,
    session: SessionDep,
    service: ServiceDep,
) -> Token:
    try:
        token = await service.login(
            payload.email, payload.password, ip=_client_ip(request)
        )
    except AppError:
        # Persist the recorded failed attempt so the rate-limit counter sticks.
        await session.commit()
        raise
    await session.commit()
    return token


@router.post("/refresh", response_model=Token)
async def refresh(
    payload: RefreshRequest,
    session: SessionDep,
    service: ServiceDep,
) -> Token:
    try:
        token = await service.refresh(payload.refresh_token)
    except AppError:
        # Persist reuse-detection family revocation even though we return 401.
        await session.commit()
        raise
    await session.commit()
    return token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    session: SessionDep,
    service: ServiceDep,
) -> None:
    await service.logout(payload.refresh_token)
    await session.commit()


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    session: SessionDep,
    service: ServiceDep,
) -> MessageResponse:
    await service.verify_email(payload.token)
    await session.commit()
    return MessageResponse(detail="Email verified.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    session: SessionDep,
    service: ServiceDep,
) -> MessageResponse:
    await service.resend_verification(payload.email)
    await session.commit()
    return MessageResponse(detail="If the account exists, a new email was sent.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: SessionDep,
    service: ServiceDep,
) -> MessageResponse:
    await service.forgot_password(payload.email, ip=_client_ip(request))
    await session.commit()
    return MessageResponse(detail="If the account exists, a reset email was sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    session: SessionDep,
    service: ServiceDep,
) -> MessageResponse:
    await service.reset_password(payload.token, payload.new_password)
    await session.commit()
    return MessageResponse(detail="Password updated.")


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
