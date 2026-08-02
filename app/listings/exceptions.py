from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError


class ListingNotFoundError(NotFoundError):
    code = "listing_not_found"
    message = "Listing not found."


class NotListingOwnerError(ForbiddenError):
    code = "not_listing_owner"
    message = "You do not own this listing."


class InvalidStatusTransitionError(ConflictError):
    code = "invalid_status_transition"
    message = "This status transition is not allowed."
