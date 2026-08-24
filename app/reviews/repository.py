import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.reviews.models import Review


class ReviewRepository:
    """Data-access for listing reviews (epic vacances)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_listing_author(
        self, listing_id: uuid.UUID, author_id: uuid.UUID
    ) -> Review | None:
        result = await self.session.execute(
            select(Review).where(
                Review.listing_id == listing_id,
                Review.author_id == author_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        listing_id: uuid.UUID,
        author_id: uuid.UUID,
        rating: int,
        comment: str | None,
    ) -> Review:
        review = Review(
            listing_id=listing_id,
            author_id=author_id,
            rating=rating,
            comment=comment,
        )
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(review)
        return review

    async def list_by_listing(self, listing_id: uuid.UUID) -> list[tuple[Review, str | None]]:
        """Reviews for a listing with the author's display name, newest first."""
        result = await self.session.execute(
            select(Review, User.full_name)
            .join(User, User.id == Review.author_id)
            .where(Review.listing_id == listing_id)
            .order_by(Review.created_at.desc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def aggregate(self, listing_id: uuid.UUID) -> tuple[float | None, int]:
        result = await self.session.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.listing_id == listing_id
            )
        )
        avg, count = result.one()
        return (float(avg) if avg is not None else None, int(count))
