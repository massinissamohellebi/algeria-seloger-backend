import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    account_type: str = Field(default="particulier", max_length=20)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    phone: str | None = None
    avatar_url: str | None = None
    # `wilaya` is the localised name (read-only, from the FK); `wilaya_code` is
    # the editable reference code.
    wilaya: str | None = None
    wilaya_code: str | None = None
    bio: str | None = None
    account_type: str = "particulier"
    # Canonical role (particulier/agence/admin), derived from account_type +
    # is_admin. Read-only: never client-settable via register/update.
    role: str = "particulier"
    is_active: bool
    is_admin: bool
    is_email_verified: bool = False
    language: str = "fr"
    email_notifications: bool = True
    created_at: datetime


class UserUpdate(BaseModel):
    """Editable profile fields (all optional; email/password are separate)."""

    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    wilaya_code: str | None = Field(default=None, min_length=2, max_length=2)
    bio: str | None = Field(default=None, max_length=500)
    account_type: str | None = Field(default=None, max_length=20)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    """Token pair returned by login / refresh.

    `refresh_token` is optional so existing access-only callers keep working,
    but login and refresh always populate it.
    """

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


# --- Email verification (Story 2) -------------------------------------------


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


# --- Forgot / reset password (Story 3) --------------------------------------


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)


# --- Refresh / logout (Story 4) ---------------------------------------------


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=256)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=256)


class MessageResponse(BaseModel):
    """Generic, enumeration-safe acknowledgement."""

    detail: str
