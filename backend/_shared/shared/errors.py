"""Application exception hierarchy.

Each exception carries the HTTP status code and machine-readable ``code`` it maps
to. ``shared.http`` serialises any :class:`AppError` into the standard error
envelope, so service code simply raises the appropriate exception.
"""

from typing import List, Optional


class AppError(Exception):
    """Base application error mapped to an HTTP 500 by default."""

    status_code: int = 500
    code: str = "internal_error"
    default_message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[List[dict]] = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or []
        super().__init__(self.message)


class ValidationError(AppError):
    """Request failed schema or business-rule validation (HTTP 400)."""

    status_code = 400
    code = "validation_error"
    default_message = "The request is invalid."


class NotFoundError(AppError):
    """Requested resource does not exist (HTTP 404)."""

    status_code = 404
    code = "not_found"
    default_message = "The requested resource was not found."


class ConflictError(AppError):
    """Request conflicts with the current state, e.g. a uniqueness violation (HTTP 409)."""

    status_code = 409
    code = "conflict"
    default_message = "The request conflicts with existing data."


class Unauthenticated(AppError):
    """Missing or invalid credentials (HTTP 401)."""

    status_code = 401
    code = "unauthenticated"
    default_message = "Authentication is required."


class Forbidden(AppError):
    """Authenticated but not permitted to perform the action (HTTP 403)."""

    status_code = 403
    code = "forbidden"
    default_message = "You do not have permission to perform this action."
