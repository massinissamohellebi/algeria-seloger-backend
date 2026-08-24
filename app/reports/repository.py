import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import User
from app.listings.models import Listing
from app.reports.models import Report, ReportReason, ReportStatus


class ReportRepository:
    """Data-access for reports + admin-queue previews (batch, no N+1)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        reporter_id: uuid.UUID | None,
        reason: ReportReason,
        message: str | None,
        listing_id: uuid.UUID | None,
        reported_user_id: uuid.UUID | None,
    ) -> Report:
        report = Report(
            reporter_id=reporter_id,
            reason=reason,
            message=message,
            listing_id=listing_id,
            reported_user_id=reported_user_id,
        )
        self.session.add(report)
        await self.session.flush()
        await self.session.refresh(report)
        return report

    async def get_by_id(self, report_id: uuid.UUID) -> Report | None:
        return await self.session.get(Report, report_id)

    async def update(self, report: Report, data: dict) -> Report:
        for key, value in data.items():
            setattr(report, key, value)
        await self.session.flush()
        await self.session.refresh(report)
        return report

    async def list_filtered(
        self,
        *,
        status: ReportStatus | None,
        reason: ReportReason | None,
        target_type: str | None,
        page: int,
        size: int,
    ) -> tuple[list[Report], int]:
        conditions = []
        if status is not None:
            conditions.append(Report.status == status)
        if reason is not None:
            conditions.append(Report.reason == reason)
        if target_type == "listing":
            conditions.append(Report.listing_id.isnot(None))
        elif target_type == "user":
            conditions.append(Report.reported_user_id.isnot(None))

        count_stmt = select(func.count()).select_from(Report)
        stmt = select(Report)
        for cond in conditions:
            count_stmt = count_stmt.where(cond)
            stmt = stmt.where(cond)

        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = (
            stmt.order_by(Report.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = list((await self.session.execute(stmt)).scalars())
        return rows, int(total)

    # --- Batch previews / counts -------------------------------------------

    async def listings_preview(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Listing]:
        if not ids:
            return {}
        result = await self.session.execute(
            select(Listing)
            .where(Listing.id.in_(ids))
            .options(selectinload(Listing.photos))
        )
        return {listing.id: listing for listing in result.scalars()}

    async def users_preview(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, User]:
        if not ids:
            return {}
        result = await self.session.execute(select(User).where(User.id.in_(ids)))
        return {user.id: user for user in result.scalars()}

    async def open_counts_by_listing(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not ids:
            return {}
        result = await self.session.execute(
            select(Report.listing_id, func.count())
            .where(Report.listing_id.in_(ids), Report.status == ReportStatus.open)
            .group_by(Report.listing_id)
        )
        return {row[0]: row[1] for row in result.all()}

    async def open_counts_by_user(
        self, ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not ids:
            return {}
        result = await self.session.execute(
            select(Report.reported_user_id, func.count())
            .where(
                Report.reported_user_id.in_(ids),
                Report.status == ReportStatus.open,
            )
            .group_by(Report.reported_user_id)
        )
        return {row[0]: row[1] for row in result.all()}
