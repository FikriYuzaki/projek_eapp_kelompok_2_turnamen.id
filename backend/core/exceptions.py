"""Domain and application exceptions mapped cleanly to REST API error codes."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base exception for all Turnamen.in domain and service errors."""

    error_code: str = "DOMAIN_ERROR"
    http_status: int = 400

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DomainValidationError(DomainError):
    """Raised when input data or domain rules (scores, quotas, dates) fail validation."""

    error_code = "VALIDATION_ERROR"
    http_status = 400


class DomainUnauthorizedError(DomainError):
    """Raised when authentication credentials or session tokens are missing or invalid."""

    error_code = "UNAUTHORIZED"
    http_status = 401


class DomainForbiddenError(DomainError):
    """Raised when an authenticated user lacks role permissions for an action."""

    error_code = "FORBIDDEN"
    http_status = 403


class DomainNotFoundError(DomainError):
    """Raised when a requested entity does not exist."""

    error_code = "NOT_FOUND"
    http_status = 404


class DomainConflictError(DomainError):
    """Raised on duplicate registrations, unique constraint violations, or locked matches."""

    error_code = "CONFLICT"
    http_status = 409
