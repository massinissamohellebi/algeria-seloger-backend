from app.core.exceptions import NotFoundError


class ReportNotFoundError(NotFoundError):
    code = "report_not_found"
    message = "Report not found."


class ReportTargetNotFoundError(NotFoundError):
    code = "report_target_not_found"
    message = "The reported listing or user does not exist."
