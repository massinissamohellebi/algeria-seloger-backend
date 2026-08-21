import uuid
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserStatus
from app.listings.models import Listing
from app.reports.models import Report


def _as_date(value: object) -> date:
    """Normalise a grouped day key (date on Postgres, str on SQLite)."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value)[:10])


class AdminRepository:
    """Data-access for admin user management + analytics aggregates."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- User management (Story 4) -----------------------------------------

    async def list_users(
        self,
        *,
        search: str | None,
        status: UserStatus | None,
        page: int,
        size: int,
    ) -> tuple[list[User], int]:
        conditions = []
        if status is not None:
            conditions.append(User.status == status)
        if search:
            like = f"%{search.strip()}%"
            conditions.append(or_(User.email.ilike(like), User.full_name.ilike(like)))

        count_stmt = select(func.count()).select_from(User)
        stmt = select(User)
        for cond in conditions:
            count_stmt = count_stmt.where(cond)
            stmt = stmt.where(cond)

        total = (await self.session.execute(count_stmt)).scalar_one()
        stmt = (
            stmt.order_by(User.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        users = list((await self.session.execute(stmt)).scalars())
        return users, int(total)

    # --- Analytics (Story 6) -----------------------------------------------

    async def count(self, model) -> int:
        result = await self.session.execute(select(func.count()).select_from(model))
        return int(result.scalar_one())

    async def active_user_ids_since(self, since: datetime) -> set[uuid.UUID]:
        """Distinct users with any activity since `since` — registration,
        a new listing, or a report (a pragmatic DAU/MAU proxy without an
        activity log)."""
        registered = select(User.id).where(User.created_at >= since)
        owners = select(Listing.owner_id).where(Listing.created_at >= since)
        reporters = select(Report.reporter_id).where(
            Report.created_at >= since, Report.reporter_id.isnot(None)
        )
        ids: set[uuid.UUID] = set()
        for stmt in (registered, owners, reporters):
            ids.update((await self.session.execute(stmt)).scalars())
        ids.discard(None)
        return ids

    async def _series(self, column, created_at, start: datetime, end: datetime):
        day = func.date(created_at)
        result = await self.session.execute(
            select(day, func.count())
            .where(created_at >= start, created_at < end)
            .group_by(day)
            .order_by(day)
        )
        return [(_as_date(row[0]), int(row[1])) for row in result.all()]

    async def listings_per_day(self, start: datetime, end: datetime):
        return await self._series(Listing.id, Listing.created_at, start, end)

    async def reports_per_day(self, start: datetime, end: datetime):
        return await self._series(Report.id, Report.created_at, start, end)

    async def top_report_reasons(self, limit: int = 5):
        result = await self.session.execute(
            select(Report.reason, func.count())
            .group_by(Report.reason)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [(str(row[0]), int(row[1])) for row in result.all()]

    async def top_wilayas(self, limit: int = 5):
        result = await self.session.execute(
            select(Listing.wilaya, func.count())
            .group_by(Listing.wilaya)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [(str(row[0]), int(row[1])) for row in result.all()]
