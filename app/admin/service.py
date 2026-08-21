import uuid
from datetime import UTC, date, datetime, time, timedelta
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.exceptions import CannotModerateSelfError
from app.admin.repository import AdminRepository
from app.admin.schemas import (
    AdminUserPage,
    AnalyticsResponse,
    LabelCount,
    TimePoint,
)
from app.auth.exceptions import UserNotFoundError
from app.auth.models import User, UserStatus
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.listings.models import Listing


class AdminService:
    """User management + analytics for admins (epic 10)."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = AdminRepository(session)
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    # --- User management (Story 4) -----------------------------------------

    async def list_users(
        self,
        *,
        search: str | None,
        status: UserStatus | None,
        page: int,
        size: int,
    ) -> AdminUserPage:
        users, total = await self.repo.list_users(
            search=search, status=status, page=page, size=size
        )
        return AdminUserPage(
            items=users,
            total=total,
            page=page,
            size=size,
            pages=ceil(total / size) if size else 0,
        )

    async def _target(self, admin: User, user_id: uuid.UUID) -> User:
        if user_id == admin.id:
            raise CannotModerateSelfError()
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    async def suspend(
        self, admin: User, user_id: uuid.UUID, suspended_until: datetime
    ) -> User:
        user = await self._target(admin, user_id)
        await self.users.update(
            user,
            {"status": UserStatus.suspended, "suspended_until": suspended_until},
        )
        await self._revoke_sessions(user)
        return user

    async def ban(self, admin: User, user_id: uuid.UUID) -> User:
        user = await self._target(admin, user_id)
        await self.users.update(
            user, {"status": UserStatus.banned, "suspended_until": None}
        )
        await self._revoke_sessions(user)
        return user

    async def reactivate(self, admin: User, user_id: uuid.UUID) -> User:
        user = await self._target(admin, user_id)
        await self.users.update(
            user, {"status": UserStatus.active, "suspended_until": None}
        )
        return user

    async def _revoke_sessions(self, user: User) -> None:
        await self.refresh_tokens.revoke_all_for_user(user.id, now=datetime.now(UTC))

    # --- Analytics (Story 6) -----------------------------------------------

    async def get_analytics(
        self, date_from: date, date_to: date
    ) -> AnalyticsResponse:
        now = datetime.now(UTC)
        dau = len(await self.repo.active_user_ids_since(now - timedelta(days=1)))
        mau = len(await self.repo.active_user_ids_since(now - timedelta(days=30)))

        start = datetime.combine(date_from, time.min, tzinfo=UTC)
        end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)

        listings = await self.repo.listings_per_day(start, end)
        reports = await self.repo.reports_per_day(start, end)

        return AnalyticsResponse(
            date_from=date_from,
            date_to=date_to,
            dau=dau,
            mau=mau,
            total_users=await self.repo.count(User),
            total_listings=await self.repo.count(Listing),
            # No messaging feature yet (epic C1) — conversations stay at zero.
            total_conversations=0,
            listings_per_day=[TimePoint(date=d, count=c) for d, c in listings],
            conversations_per_day=[],
            reports_per_day=[TimePoint(date=d, count=c) for d, c in reports],
            top_report_reasons=[
                LabelCount(label=label, count=count)
                for label, count in await self.repo.top_report_reasons()
            ],
            top_wilayas=[
                LabelCount(label=label, count=count)
                for label, count in await self.repo.top_wilayas()
            ],
        )
