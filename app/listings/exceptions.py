from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)


class ListingNotFoundError(NotFoundError):
    code = "listing_not_found"
    message = "Listing not found."


class PhotoNotFoundError(NotFoundError):
    code = "photo_not_found"
    message = "Photo not found."


class MaxPhotosReachedError(ConflictError):
    code = "max_photos_reached"
    message = "This listing already has the maximum number of photos."


class InvalidPhotoError(AppError):
    status_code = 422
    code = "invalid_photo"
    message = "The uploaded file is not a valid image."


class NotListingOwnerError(ForbiddenError):
    code = "not_listing_owner"
    message = "You do not own this listing."


class InvalidStatusTransitionError(ConflictError):
    code = "invalid_status_transition"
    message = "This status transition is not allowed."
