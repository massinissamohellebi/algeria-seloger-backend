import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.reports.models import ReportReason, ReportStatus


class ReportCreate(BaseModel):
    reason: ReportReason
    message: str | None = Field(default=None, max_length=2000)
    listing_id: uuid.UUID | None = None
    reported_user_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _exactly_one_target(self) -> "ReportCreate":
        if (self.listing_id is None) == (self.reported_user_id is None):
            raise ValueError(
                "Provide exactly one target: listing_id or reported_user_id."
            )
        return self


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reason: ReportReason
    message: str | None
    status: ReportStatus
    reporter_id: uuid.UUID | None
    listing_id: uuid.UUID | None
    reported_user_id: uuid.UUID | None
    created_at: datetime


# --- Admin report queue (Story 3) ------------------------------------------


class ReportTargetPreview(BaseModel):
    """Lightweight target context so the queue avoids N+1 lookups."""

    type: Literal["listing", "user"]
    id: uuid.UUID
    label: str
    cover_url: str | None = None


class AdminReportRead(BaseModel):
    id: uuid.UUID
    reason: ReportReason
    message: str | None
    status: ReportStatus
    reporter_id: uuid.UUID | None
    reporter_email: str | None
    admin_note: str | None
    resolved_by: uuid.UUID | None
    created_at: datetime
    target: ReportTargetPreview
    # Number of open reports against the same target (dedupe signal).
    target_report_count: int


class AdminReportPage(BaseModel):
    items: list[AdminReportRead]
    total: int
    page: int
    size: int
    pages: int


class ReportUpdate(BaseModel):
    status: Literal["resolved", "dismissed"]
    admin_note: str | None = Field(default=None, max_length=2000)
