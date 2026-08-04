import uuid

from app.auth.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.auth.models import User
from app.auth.repository import UserRepository
from app.auth.schemas import Token, UserCreate, UserUpdate
from app.core.security import (
    JWTError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class AuthService:
    """Business logic for authentication and user identity."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def register(self, payload: UserCreate) -> User:
        existing = await self.repository.get_by_email(payload.email)
        if existing is not None:
            raise EmailAlreadyExistsError()
        return await self.repository.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            phone=payload.phone,
            account_type=payload.account_type,
        )

    async def update_profile(self, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        return await self.repository.update(user, data)

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError()
        await self.repository.update(
            user, {"hashed_password": hash_password(new_password)}
        )

    async def delete_account(self, user: User) -> None:
        await self.repository.delete(user)

    async def login(self, email: str, password: str) -> Token:
        user = await self.repository.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()
        token = create_access_token(subject=str(user.id))
        return Token(access_token=token)

    async def get_current_user(self, token: str) -> User:
        user = await self._resolve_user_from_token(token)
        if not user.is_active:
            raise InactiveUserError()
        return user

    async def _resolve_user_from_token(self, token: str) -> User:
        user_id = _extract_subject(token)
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise InvalidTokenError()
        return user


def _extract_subject(token: str) -> uuid.UUID:
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise InvalidTokenError() from exc
    subject = payload.get("sub")
    if subject is None:
        raise InvalidTokenError()
    try:
        return uuid.UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError() from exc
