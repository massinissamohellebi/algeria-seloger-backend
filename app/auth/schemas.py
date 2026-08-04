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
    wilaya: str | None = None
    bio: str | None = None
    account_type: str = "particulier"
    is_active: bool
    is_admin: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Editable profile fields (all optional; email/password are separate)."""

    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    wilaya: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=500)
    account_type: str | None = Field(default=None, max_length=20)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
