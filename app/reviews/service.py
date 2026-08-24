import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.listings.exceptions import ListingNotFoundError
from app.listings.models import Listing
from app.reviews.exceptions import SelfReviewForbiddenError
from app.reviews.models import Review
from app.reviews.repository import ReviewRepository
from app.reviews.schemas import ReviewList, ReviewRead

# "Coup de coeur voyageurs" — a highly-rated, well-reviewed stay.
COUP_DE_COEUR_MIN_AVG = 4.8
COUP_DE_COEUR_MIN_COUNT = 5

_DEFAULT_AUTHOR_NAME = "Utilisateur"


def _is_coup_de_coeur(average: float | None, count: int) -> bool:
    return (
        average is not None
        and count >= COUP_DE_COEUR_MIN_COUNT
        and average >= COUP_DE_COEUR_MIN_AVG
    )


class ReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReviewRepository(session)

    async def add_review(
        self,
        author: User,
        listing_id: uuid.UUID,
        rating: int,
        comment: str | None,
    ) -> ReviewRead:
        listing = await self.session.get(Listing, listing_id)
        if listing is None:
            raise ListingNotFoundError()
        if listing.owner_id == author.id:
            raise SelfReviewForbiddenError()

        existing = await self.repo.get_by_listing_author(listing_id, author.id)
        if existing is not None:
            existing.rating = rating
            existing.comment = comment
            await self.session.flush()
            await self.session.refresh(existing)
            review = existing
        else:
            review = await self.repo.create(
                listing_id=listing_id,
                author_id=author.id,
                rating=rating,
                comment=comment,
            )
        return self._to_read(review, author.full_name)

    async def list_reviews(self, listing_id: uuid.UUID) -> ReviewList:
        rows = await self.repo.list_by_listing(listing_id)
        average, count = await self.repo.aggregate(listing_id)
        items = [self._to_read(review, name) for review, name in rows]
        return ReviewList(
            items=items,
            average=round(average, 2) if average is not None else None,
            count=count,
            coup_de_coeur=_is_coup_de_coeur(average, count),
        )

    async def aggregate(self, listing_id: uuid.UUID) -> tuple[float | None, int]:
        """Mean rating + review count, for the listing detail payload."""
        return await self.repo.aggregate(listing_id)

    def _to_read(self, review: Review, author_name: str | None) -> ReviewRead:
        return ReviewRead(
            id=review.id,
            listing_id=review.listing_id,
            author_id=review.author_id,
            author_name=author_name or _DEFAULT_AUTHOR_NAME,
            rating=review.rating,
            comment=review.comment,
            created_at=review.created_at,
        )
