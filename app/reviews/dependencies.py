from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.reviews.service import ReviewService


def get_review_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewService:
    return ReviewService(session)
