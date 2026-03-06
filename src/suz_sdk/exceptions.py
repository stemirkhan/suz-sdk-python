"""Typed exception hierarchy for the SUZ SDK.

All SDK exceptions derive from SuzError, so callers can catch broadly
or narrowly depending on their needs.

Error format returned by the СУЗ API (§6.2):
    {
        "fieldErrors": [{"fieldError": "...", "fieldName": "...", "errorCode": "..."}],
        "globalErrors": [{"error": "...", "errorCode": "..."}],
        "success": false
    }
"""

from typing import Any


class SuzError(Exception):
    """Base exception for all SUZ SDK errors."""


# ---------------------------------------------------------------------------
# Transport-level errors
# ---------------------------------------------------------------------------


class SuzTransportError(SuzError):
    """Raised when a network-level failure occurs (connection refused, DNS, etc.)."""


class SuzTimeoutError(SuzTransportError):
    """Raised when a request exceeds the configured timeout."""


# ---------------------------------------------------------------------------
# Auth errors
# ---------------------------------------------------------------------------


class SuzAuthError(SuzError):
    """Raised when authentication or authorization fails (HTTP 401)."""


class SuzTokenExpiredError(SuzAuthError):
    """Raised when the clientToken has expired and must be refreshed."""


# ---------------------------------------------------------------------------
# Signing errors
# ---------------------------------------------------------------------------


class SuzSignatureError(SuzError):
    """Raised when a signature is rejected by the server.

    The API returns HTTP 413 when an attached (non-detached) signature is
    provided in X-Signature. Only detached CMS signatures are supported.
    """


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class SuzValidationError(SuzError):
    """Raised for HTTP 400 — invalid request parameters or payload schema."""


# ---------------------------------------------------------------------------
# General API error
# ---------------------------------------------------------------------------


class SuzApiError(SuzError):
    """Raised for error responses from the СУЗ API.

    Attributes:
        status_code: HTTP status code returned by the server.
        error_code:  СУЗ-specific error code from the response body, if present.
        raw_body:    Full parsed response body (dict / str), for diagnostics.
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: str | None = None,
        raw_body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.raw_body = raw_body

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status_code={self.status_code}, "
            f"error_code={self.error_code!r}, "
            f"message={str(self)!r})"
        )


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class SuzRateLimitError(SuzError):
    """Raised when the server signals that request rate limit is exceeded."""
