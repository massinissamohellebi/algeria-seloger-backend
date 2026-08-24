from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError


class SelfContactForbiddenError(BadRequestError):
    code = "self_contact_forbidden"
    message = "You cannot contact your own listing."


class ConversationNotFoundError(NotFoundError):
    code = "conversation_not_found"
    message = "Conversation not found."


class NotParticipantError(ForbiddenError):
    code = "not_conversation_participant"
    message = "You are not a participant in this conversation."
