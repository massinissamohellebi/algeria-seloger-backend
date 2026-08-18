from app.core.exceptions import BadRequestError


class UnsupportedAvatarTypeError(BadRequestError):
    code = "unsupported_avatar_type"
    message = "Avatar must be a JPEG, PNG or WebP image."


class AvatarTooLargeError(BadRequestError):
    code = "avatar_too_large"
    message = "Avatar file exceeds the maximum allowed size."


class EmptyAvatarError(BadRequestError):
    code = "empty_avatar"
    message = "The uploaded avatar file is empty."
