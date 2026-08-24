import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.reviews.dependencies import get_review_service
from app.reviews.schemas import ReviewCreate, ReviewList, ReviewRead
from app.reviews.service import ReviewService

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[ReviewService, Depends(get_review_service)]

router = APIRouter(prefix="/listings", tags=["reviews"])


@router.get("/{listing_id}/reviews", response_model=ReviewList)
async def list_reviews(
    listing_id: uuid.UUID,
    service: ServiceDep,
) -> ReviewList:
    return await service.list_reviews(listing_id)


@router.post(
    "/{listing_id}/reviews",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    listing_id: uuid.UUID,
    payload: ReviewCreate,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> ReviewRead:
    review = await service.add_review(current_user, listing_id, payload.rating, payload.comment)
    await session.commit()
    return review
