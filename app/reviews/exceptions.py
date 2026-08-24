from app.core.exceptions import BadRequestError


class SelfReviewForbiddenError(BadRequestError):
    code = "self_review_forbidden"
    message = "You cannot review your own listing."
