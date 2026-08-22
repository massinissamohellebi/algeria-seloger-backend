import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.models import Conversation, Message


class MessagingRepository:
    """Data-access for conversations & messages (epic 05)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Conversations -----------------------------------------------------

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def get_by_listing_enquirer(
        self, listing_id: uuid.UUID, enquirer_id: uuid.UUID
    ) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.listing_id == listing_id,
                Conversation.enquirer_id == enquirer_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_conversation(
        self,
        *,
        listing_id: uuid.UUID,
        enquirer_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Conversation:
        conv = Conversation(
            listing_id=listing_id, enquirer_id=enquirer_id, owner_id=owner_id
        )
        self.session.add(conv)
        await self.session.flush()
        await self.session.refresh(conv)
        return conv

    async def list_for_user(self, user_id: uuid.UUID) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .where(
                or_(
                    Conversation.enquirer_id == user_id,
                    Conversation.owner_id == user_id,
                )
            )
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars())

    # --- Messages ----------------------------------------------------------

    async def create_message(
        self, *, conversation_id: uuid.UUID, sender_id: uuid.UUID, body: str
    ) -> Message:
        message = Message(
            conversation_id=conversation_id, sender_id=sender_id, body=body
        )
        self.session.add(message)
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.now(UTC))
        )
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def messages_paginated(
        self, conversation_id: uuid.UUID, page: int, per_page: int
    ) -> tuple[list[Message], int]:
        base = select(Message).where(Message.conversation_id == conversation_id)
        total = (
            await self.session.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        result = await self.session.execute(
            base.order_by(Message.created_at.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return list(result.scalars()), int(total)

    async def mark_read(
        self, conversation_id: uuid.UUID, reader_id: uuid.UUID
    ) -> None:
        await self.session.execute(
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sender_id != reader_id,
                Message.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self.session.flush()

    async def unread_count(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(Message.id))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                or_(
                    Conversation.enquirer_id == user_id,
                    Conversation.owner_id == user_id,
                ),
                Message.sender_id != user_id,
                Message.is_read.is_(False),
            )
        )
        return int(result.scalar_one())

    # --- Batch helpers for the conversation list ---------------------------

    async def last_messages(
        self, conversation_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Message]:
        if not conversation_ids:
            return {}
        latest = (
            select(
                Message.conversation_id,
                func.max(Message.created_at).label("mx"),
            )
            .where(Message.conversation_id.in_(conversation_ids))
            .group_by(Message.conversation_id)
            .subquery()
        )
        result = await self.session.execute(
            select(Message).join(
                latest,
                and_(
                    Message.conversation_id == latest.c.conversation_id,
                    Message.created_at == latest.c.mx,
                ),
            )
        )
        out: dict[uuid.UUID, Message] = {}
        for message in result.scalars():
            out.setdefault(message.conversation_id, message)
        return out

    async def unread_by_conversation(
        self, conversation_ids: list[uuid.UUID], user_id: uuid.UUID
    ) -> dict[uuid.UUID, int]:
        if not conversation_ids:
            return {}
        result = await self.session.execute(
            select(Message.conversation_id, func.count())
            .where(
                Message.conversation_id.in_(conversation_ids),
                Message.sender_id != user_id,
                Message.is_read.is_(False),
            )
            .group_by(Message.conversation_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}
