from app.core.exceptions import ForbiddenError, NotFoundError


class NotificationNotFoundError(NotFoundError):
    code = "notification_not_found"
    message = "Notification not found."


class NotOwnNotificationError(ForbiddenError):
    code = "not_own_notification"
    message = "This notification does not belong to you."
