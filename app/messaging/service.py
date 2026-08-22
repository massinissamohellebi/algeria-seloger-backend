import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.listings.exceptions import ListingNotFoundError
from app.listings.models import Listing, ListingPhoto, ListingStatus
from app.messaging.exceptions import (
    ConversationNotFoundError,
    NotParticipantError,
    SelfContactForbiddenError,
)
from app.messaging.models import Conversation, Message
from app.messaging.repository import MessagingRepository
from app.messaging.schemas import (
    ConversationList,
    ConversationRead,
    ConversationStart,
    ListingPreview,
    MessagePage,
    MessageRead,
)


class MessagingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MessagingRepository(session)

    # --- Start / resume (C2) -----------------------------------------------

    async def start_or_resume(
        self, enquirer: User, data: ConversationStart
    ) -> tuple[Conversation, bool]:
        listing = await self.session.get(Listing, data.listing_id)
        if listing is None or listing.status != ListingStatus.published:
            raise ListingNotFoundError()
        if listing.owner_id == enquirer.id:
            raise SelfContactForbiddenError()

        existing = await self.repo.get_by_listing_enquirer(
            data.listing_id, enquirer.id
        )
        if existing is not None:
            await self.repo.create_message(
                conversation_id=existing.id,
                sender_id=enquirer.id,
                body=data.initial_message,
            )
            return existing, False

        conv = await self.repo.create_conversation(
            listing_id=data.listing_id,
            enquirer_id=enquirer.id,
            owner_id=listing.owner_id,
        )
        await self.repo.create_message(
            conversation_id=conv.id,
            sender_id=enquirer.id,
            body=data.initial_message,
        )
        return conv, True

    async def find_for_listing(
        self, listing_id: uuid.UUID, user: User
    ) -> Conversation | None:
        """The enquirer's existing conversation on a listing (for the CTA)."""
        return await self.repo.get_by_listing_enquirer(listing_id, user.id)

    # --- Participation guard -----------------------------------------------

    async def _assert_participant(
        self, conversation_id: uuid.UUID, user: User
    ) -> Conversation:
        conv = await self.repo.get_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundError()
        if user.id not in (conv.enquirer_id, conv.owner_id):
            raise NotParticipantError()
        return conv

    # --- List / thread / send / read / unread (C3) -------------------------

    async def read_one(self, conv: Conversation, user: User) -> ConversationRead:
        last = await self.repo.last_messages([conv.id])
        unread = await self.repo.unread_by_conversation([conv.id], user.id)
        covers = await self._cover_urls(
            [conv.listing_id] if conv.listing_id else []
        )
        return self._to_read(conv, last, unread, covers)

    async def list_conversations(self, user: User) -> ConversationList:
        convs = await self.repo.list_for_user(user.id)
        conv_ids = [c.id for c in convs]
        last = await self.repo.last_messages(conv_ids)
        unread = await self.repo.unread_by_conversation(conv_ids, user.id)
        covers = await self._cover_urls(
            [c.listing_id for c in convs if c.listing_id]
        )

        items = [self._to_read(c, last, unread, covers) for c in convs]
        return ConversationList(items=items, total=len(items))

    def _to_read(
        self,
        conv: Conversation,
        last: dict,
        unread: dict,
        covers: dict,
    ) -> ConversationRead:
        preview = None
        if conv.listing is not None:
            preview = ListingPreview(
                id=conv.listing.id,
                title=conv.listing.title,
                cover_url=covers.get(conv.listing.id),
            )
        last_msg = last.get(conv.id)
        return ConversationRead(
            id=conv.id,
            listing_id=conv.listing_id,
            enquirer_id=conv.enquirer_id,
            owner_id=conv.owner_id,
            updated_at=conv.updated_at,
            listing=preview,
            last_message=MessageRead.model_validate(last_msg) if last_msg else None,
            unread_count=unread.get(conv.id, 0),
        )

    async def _cover_urls(
        self, listing_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, str]:
        if not listing_ids:
            return {}
        result = await self.session.execute(
            select(ListingPhoto.listing_id, ListingPhoto.url)
            .where(
                ListingPhoto.listing_id.in_(listing_ids),
                ListingPhoto.is_cover.is_(True),
            )
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_messages(
        self, conversation_id: uuid.UUID, user: User, page: int, per_page: int
    ) -> MessagePage:
        await self._assert_participant(conversation_id, user)
        messages, total = await self.repo.messages_paginated(
            conversation_id, page, per_page
        )
        # Opening the thread marks the peer's messages as read.
        await self.repo.mark_read(conversation_id, user.id)
        return MessagePage(
            items=[MessageRead.model_validate(m) for m in messages],
            total=total,
            page=page,
            per_page=per_page,
        )

    async def send_message(
        self, conversation_id: uuid.UUID, user: User, body: str
    ) -> Message:
        await self._assert_participant(conversation_id, user)
        return await self.repo.create_message(
            conversation_id=conversation_id, sender_id=user.id, body=body
        )

    async def mark_read(self, conversation_id: uuid.UUID, user: User) -> None:
        await self._assert_participant(conversation_id, user)
        await self.repo.mark_read(conversation_id, user.id)

    async def unread_count(self, user: User) -> int:
        return await self.repo.unread_count(user.id)
