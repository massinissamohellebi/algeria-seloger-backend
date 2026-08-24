import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.core.database import get_db
from app.messaging.dependencies import get_messaging_service
from app.messaging.exceptions import ConversationNotFoundError
from app.messaging.schemas import (
    ConversationList,
    ConversationRead,
    ConversationStart,
    MessageCreate,
    MessagePage,
    MessageRead,
    UnreadCount,
)
from app.messaging.service import MessagingService

SessionDep = Annotated[AsyncSession, Depends(get_db)]
ServiceDep = Annotated[MessagingService, Depends(get_messaging_service)]

router = APIRouter(prefix="/conversations", tags=["messaging"])


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    payload: ConversationStart,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
    response: Response,
) -> ConversationRead:
    conv, created = await service.start_or_resume(current_user, payload)
    await session.commit()
    if not created:
        response.status_code = status.HTTP_200_OK
    return await service.read_one(conv, current_user)


@router.get("", response_model=ConversationList)
async def list_conversations(
    current_user: CurrentUser,
    service: ServiceDep,
) -> ConversationList:
    return await service.list_conversations(current_user)


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    current_user: CurrentUser,
    service: ServiceDep,
) -> UnreadCount:
    return UnreadCount(unread_count=await service.unread_count(current_user))


@router.get("/by-listing/{listing_id}", response_model=ConversationRead)
async def conversation_by_listing(
    listing_id: uuid.UUID,
    current_user: CurrentUser,
    service: ServiceDep,
) -> ConversationRead:
    conv = await service.find_for_listing(listing_id, current_user)
    if conv is None:
        raise ConversationNotFoundError()
    return await service.read_one(conv, current_user)


@router.get("/{conversation_id}/messages", response_model=MessagePage)
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MessagePage:
    result = await service.get_messages(
        conversation_id, current_user, page, per_page
    )
    await session.commit()
    return result


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> MessageRead:
    message = await service.send_message(
        conversation_id, current_user, payload.body
    )
    await session.commit()
    return MessageRead.model_validate(message)


@router.post("/{conversation_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_read(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    session: SessionDep,
    service: ServiceDep,
) -> None:
    await service.mark_read(conversation_id, current_user)
    await session.commit()
