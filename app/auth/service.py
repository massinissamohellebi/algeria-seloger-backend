from app.auth.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.auth.models import User
from app.auth.repository import UserRepository
from app.auth.schemas import Token, UserCreate
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
        )

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


def _extract_subject(token: str) -> int:
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise InvalidTokenError() from exc
    subject = payload.get("sub")
    if subject is None:
        raise InvalidTokenError()
    try:
        return int(subject)
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError() from exc
