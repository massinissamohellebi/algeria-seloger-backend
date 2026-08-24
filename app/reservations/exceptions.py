from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError


class SelfReservationForbiddenError(BadRequestError):
    code = "self_reservation_forbidden"
    message = "You cannot reserve your own listing."


class NotVacationListingError(BadRequestError):
    code = "not_vacation_listing"
    message = "This listing is not available for vacation booking."


class InvalidDateRangeError(BadRequestError):
    code = "invalid_date_range"
    message = "The check-out date must be after the check-in date."


class TooManyGuestsError(BadRequestError):
    code = "too_many_guests"
    message = "The number of guests exceeds the accommodation capacity."


class ReservationNotFoundError(NotFoundError):
    code = "reservation_not_found"
    message = "Reservation not found."


class NotReservationHostError(ForbiddenError):
    code = "not_reservation_host"
    message = "Only the host can manage this reservation."


class ReservationNotActionableError(BadRequestError):
    code = "reservation_not_actionable"
    message = "This reservation can no longer be updated."
