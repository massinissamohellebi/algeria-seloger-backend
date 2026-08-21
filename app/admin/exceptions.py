from app.core.exceptions import ForbiddenError


class CannotModerateSelfError(ForbiddenError):
    code = "cannot_moderate_self"
    message = "An admin cannot suspend or ban their own account."
