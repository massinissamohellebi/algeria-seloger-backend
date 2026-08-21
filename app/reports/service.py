import uuid
from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.exceptions import RateLimitedError
from app.auth.models import User
from app.auth.repository import LoginAttemptRepository, UserRepository
from app.core.config import settings
from app.listings.repository import ListingRepository
from app.listings.service import _cover_url
from app.reports.exceptions import (
    ReportNotFoundError,
    ReportTargetNotFoundError,
)
from app.reports.models import Report, ReportReason, ReportStatus
from app.reports.repository import ReportRepository
from app.reports.schemas import (
    AdminReportPage,
    AdminReportRead,
    ReportCreate,
    ReportTargetPreview,
)


class ReportService:
    """Report creation (public) + admin queue triage (epic 10)."""

    def __init__(self, session: AsyncSession) -> None:
        self.reports = ReportRepository(session)
        self.listings = ListingRepository(session)
        self.users = UserRepository(session)
        self.attempts = LoginAttemptRepository(session)

    # --- Create (Story 2) --------------------------------------------------

    async def create_report(
        self, reporter: User | None, payload: ReportCreate, *, ip: str | None
    ) -> Report:
        await self._enforce_rate_limit(ip)
        await self._require_target(payload)
        await self.attempts.add(_report_identifier(ip))
        return await self.reports.create(
            reporter_id=reporter.id if reporter else None,
            reason=payload.reason,
            message=payload.message,
            listing_id=payload.listing_id,
            reported_user_id=payload.reported_user_id,
        )

    async def _require_target(self, payload: ReportCreate) -> None:
        if payload.listing_id is not None:
            if await self.listings.get_by_id(payload.listing_id) is None:
                raise ReportTargetNotFoundError()
        elif await self.users.get_by_id(payload.reported_user_id) is None:
            raise ReportTargetNotFoundError()

    async def _enforce_rate_limit(self, ip: str | None) -> None:
        window = timedelta(minutes=settings.report_rate_limit_window_minutes)
        since = datetime.now(UTC) - window
        count = await self.attempts.count_since(_report_identifier(ip), since)
        if count >= settings.report_rate_limit_max_attempts:
            raise RateLimitedError(
                retry_after=settings.report_rate_limit_window_minutes * 60
            )

    # --- Admin queue (Story 3) ---------------------------------------------

    async def list_reports(
        self,
        *,
        status: ReportStatus | None,
        reason: ReportReason | None,
        target_type: str | None,
        page: int,
        size: int,
    ) -> AdminReportPage:
        rows, total = await self.reports.list_filtered(
            status=status,
            reason=reason,
            target_type=target_type,
            page=page,
            size=size,
        )
        items = await self._assemble(rows)
        return AdminReportPage(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=ceil(total / size) if size else 0,
        )

    async def _assemble(self, rows: list[Report]) -> list[AdminReportRead]:
        listing_ids = [r.listing_id for r in rows if r.listing_id]
        user_ids = [r.reported_user_id for r in rows if r.reported_user_id]
        reporter_ids = [r.reporter_id for r in rows if r.reporter_id]

        listings = await self.reports.listings_preview(listing_ids)
        reported_users = await self.reports.users_preview(user_ids)
        reporters = await self.reports.users_preview(reporter_ids)
        listing_counts = await self.reports.open_counts_by_listing(listing_ids)
        user_counts = await self.reports.open_counts_by_user(user_ids)

        items: list[AdminReportRead] = []
        for report in rows:
            if report.listing_id is not None:
                listing = listings.get(report.listing_id)
                target = ReportTargetPreview(
                    type="listing",
                    id=report.listing_id,
                    label=listing.title if listing else "—",
                    cover_url=_cover_url(listing.photos) if listing else None,
                )
                count = listing_counts.get(report.listing_id, 0)
            else:
                user = reported_users.get(report.reported_user_id)
                target = ReportTargetPreview(
                    type="user",
                    id=report.reported_user_id,
                    label=(user.full_name or user.email) if user else "—",
                )
                count = user_counts.get(report.reported_user_id, 0)

            reporter = reporters.get(report.reporter_id) if report.reporter_id else None
            items.append(
                AdminReportRead(
                    id=report.id,
                    reason=report.reason,
                    message=report.message,
                    status=report.status,
                    reporter_id=report.reporter_id,
                    reporter_email=reporter.email if reporter else None,
                    admin_note=report.admin_note,
                    resolved_by=report.resolved_by,
                    created_at=report.created_at,
                    target=target,
                    target_report_count=count,
                )
            )
        return items

    async def update_report(
        self, report_id: uuid.UUID, admin: User, status: str, admin_note: str | None
    ) -> Report:
        report = await self.reports.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError()
        return await self.reports.update(
            report,
            {
                "status": ReportStatus(status),
                "admin_note": admin_note,
                "resolved_by": admin.id,
            },
        )


def _report_identifier(ip: str | None) -> str:
    return f"report:{ip or 'unknown'}"
