from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.repository import UserRepository
from app.auth.service import AuthService
from app.core.database import get_db
from app.core.exceptions import AppError, ForbiddenError
from app.core.mailer import Mailer, get_mailer

bearer_scheme = HTTPBearer(auto_error=True)
optional_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
) -> AuthService:
    return AuthService(UserRepository(session), mailer=mailer)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return await service.get_current_user(credentials.credentials)


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_bearer_scheme)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User | None:
    """Return the authenticated user if a valid token is present, else None.

    Used by public endpoints that reveal extra data to the owner (e.g. their
    own non-published listings) without requiring authentication.
    """
    if credentials is None:
        return None
    try:
        return await service.get_current_user(credentials.credentials)
    except AppError:
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalCurrentUser = Annotated[User | None, Depends(get_current_user_optional)]


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_admin:
        raise ForbiddenError("Admin privileges are required for this action.")
    return current_user


AdminUser = Annotated[User, Depends(get_current_admin)]
