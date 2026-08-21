import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.auth.models import UserStatus


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    avatar_url: str | None = None
    account_type: str
    role: str
    is_admin: bool
    status: UserStatus
    suspended_until: datetime | None
    created_at: datetime


class AdminUserPage(BaseModel):
    items: list[AdminUserRead]
    total: int
    page: int
    size: int
    pages: int


class SuspendRequest(BaseModel):
    suspended_until: datetime


# --- Analytics (Story 6) ----------------------------------------------------


class TimePoint(BaseModel):
    date: date
    count: int


class LabelCount(BaseModel):
    label: str
    count: int


class AnalyticsResponse(BaseModel):
    date_from: date
    date_to: date
    dau: int
    mau: int
    total_users: int
    total_listings: int
    total_conversations: int
    listings_per_day: list[TimePoint]
    conversations_per_day: list[TimePoint]
    reports_per_day: list[TimePoint]
    top_report_reasons: list[LabelCount]
    top_wilayas: list[LabelCount]
