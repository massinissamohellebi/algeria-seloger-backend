from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError


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


class UserNotFoundError(NotFoundError):
    code = "user_not_found"
    message = "User not found."
