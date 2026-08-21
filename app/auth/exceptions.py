from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
)


class EmailAlreadyExistsError(ConflictError):
    code = "email_already_exists"
    message = "A user with this email already exists."


class InvalidCredentialsError(UnauthorizedError):
    code = "invalid_credentials"
    message = "Incorrect email or password."


class InvalidTokenError(UnauthorizedError):
    code = "invalid_token"
    message = "Could not validate credentials."


class InactiveUserError(UnauthorizedError):
    code = "inactive_user"
    message = "User account is inactive."


class AccountSuspendedError(ForbiddenError):
    code = "account_suspended"
    message = "This account is suspended."


class AccountBannedError(ForbiddenError):
    code = "account_banned"
    message = "This account has been banned."


class EmailNotVerifiedError(ForbiddenError):
    code = "email_not_verified"
    message = "Please verify your email address before signing in."


class UserNotFoundError(NotFoundError):
    code = "user_not_found"
    message = "User not found."


class InvalidVerificationTokenError(BadRequestError):
    # Generic on purpose: never reveals expired vs unknown vs consumed.
    code = "invalid_verification_token"
    message = "This verification link is invalid or has expired."


class InvalidResetTokenError(BadRequestError):
    code = "invalid_reset_token"
    message = "This reset link is invalid or has expired."


class InvalidRefreshTokenError(UnauthorizedError):
    code = "invalid_refresh_token"
    message = "The refresh token is invalid, expired or revoked."


class RateLimitedError(TooManyRequestsError):
    code = "rate_limited"
    message = "Too many attempts. Please wait before trying again."
