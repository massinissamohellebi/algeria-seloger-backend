from typing import Literal

from pydantic import BaseModel, Field

# Strict allow-list of supported UI languages (epic 9, story 2).
Language = Literal["fr", "en", "ar"]


class ProfileUpdate(BaseModel):
    """Editable profile fields. Email and role are immutable via this endpoint."""

    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    wilaya: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=500)


class PreferencesUpdate(BaseModel):
    language: Language | None = None
    email_notifications: bool | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    detail: str
