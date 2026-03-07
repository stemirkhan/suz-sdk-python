"""httpx-based transport implementation for the SUZ SDK.

This is the default, production-ready transport.  It handles:
- Base URL construction
- Request serialization and response deserialization
- Timeout enforcement
- Automatic retries with exponential backoff (via RetryConfig)
- Structured logging (method, path, status, elapsed) without leaking secrets
- HTTP error → SDK exception mapping per §6.2 of the API specification

Error code mapping (§6.2.2):
    400 → SuzValidationError   (invalid input parameters)
    401 → SuzAuthError         (token missing or invalid)
    404 → SuzApiError          (object not found)
    413 → SuzSignatureError    (attached signature not supported)
    500 → SuzApiError          (server-side error; retry after 30s per spec)
"""

import logging
import time
from typing import Any

import httpx

from suz_sdk.exceptions import (
    SuzApiError,
    SuzAuthError,
    SuzSignatureError,
    SuzTimeoutError,
    SuzTransportError,
    SuzValidationError,
)
from suz_sdk.transport.base import Request, Response
from suz_sdk.transport.retry import RetryConfig

logger = logging.getLogger(__name__)

# Default User-Agent; callers can override via SuzConfig.user_agent
_DEFAULT_USER_AGENT = "suz-sdk-python/0.1.0"


class HttpxTransport:
    """Synchronous HTTP transport backed by httpx.Client.

    The client is intended to be long-lived (reuses a connection pool).
    Use as a context manager or call ``close()`` when done.

    Args:
        base_url:   Base URL for all requests, e.g.
                    "https://suz-integrator.sandbox.crptech.ru".
                    Trailing slashes are stripped.
        timeout:    Request timeout in seconds.  Applies to connect + read.
        verify_ssl: Whether to verify TLS certificates.  Set to False only
                    in controlled test environments.
        user_agent: Value for the User-Agent header.
        retry:      Optional retry configuration.  When provided, failed
                    requests are automatically retried according to the policy.
                    Pass ``RetryConfig()`` to use the defaults (3 retries,
                    exponential backoff, retry on 5xx and network errors).
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        user_agent: str = _DEFAULT_USER_AGENT,
        retry: RetryConfig | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._retry = retry
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            verify=verify_ssl,
        )

    def request(self, req: Request) -> Response:
        """Execute an HTTP request and return a parsed Response.

        When a ``RetryConfig`` is configured, automatically retries on the
        specified status codes and/or network errors with exponential backoff.

        Logs method, path, status code, and elapsed time.
        Never logs header values (tokens, signatures).

        Args:
            req: The request descriptor.

        Returns:
            Parsed Response object (2xx only).

        Raises:
            SuzTimeoutError:    Request exceeded the configured timeout.
            SuzTransportError:  Network-level failure (DNS, connection).
            SuzValidationError: HTTP 400.
            SuzAuthError:       HTTP 401.
            SuzSignatureError:  HTTP 413.
            SuzApiError:        Any other non-2xx response.
        """
        max_attempts = 1 + (self._retry.max_retries if self._retry else 0)
        last_resp: Response | None = None

        for attempt in range(max_attempts):
            try:
                resp = self._send(req)
                last_resp = resp
            except (SuzTimeoutError, SuzTransportError) as exc:
                if (
                    self._retry
                    and self._retry.retry_on_network_errors
                    and attempt < max_attempts - 1
                ):
                    wait = self._retry.backoff_factor * (2 ** attempt)
                    logger.warning(
                        "Retry %d/%d for %s %s after network error: %s, sleeping %.2fs",
                        attempt + 1,
                        self._retry.max_retries,
                        req.method,
                        req.path,
                        exc,
                        wait,
                    )
                    time.sleep(wait)
                    continue
                raise

            if (
                self._retry
                and resp.status_code in self._retry.retry_statuses
                and attempt < max_attempts - 1
            ):
                wait = self._retry.backoff_factor * (2 ** attempt)
                logger.warning(
                    "Retry %d/%d for %s %s after HTTP %d, sleeping %.2fs",
                    attempt + 1,
                    self._retry.max_retries,
                    req.method,
                    req.path,
                    resp.status_code,
                    wait,
                )
                time.sleep(wait)
                continue

            self._raise_for_status(resp, req)
            return resp

        # All retries exhausted — raise from the last response.
        assert last_resp is not None
        self._raise_for_status(last_resp, req)
        return last_resp  # unreachable; _raise_for_status always raises here

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send(self, req: Request) -> Response:
        """Execute a single HTTP attempt and return the raw Response.

        Does NOT call ``_raise_for_status``; the caller decides whether to
        retry or raise.  Always raises ``SuzTimeoutError`` / ``SuzTransportError``
        on network-level failures.
        """
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
            **req.headers,
        }

        logger.debug("→ %s %s params=%s", req.method, req.path, list(req.params.keys()))
        start = time.monotonic()

        try:
            if req.raw_body is not None:
                raw = self._client.request(
                    method=req.method,
                    url=req.path,
                    params=req.params or None,
                    headers=headers,
                    content=req.raw_body,
                )
            else:
                raw = self._client.request(
                    method=req.method,
                    url=req.path,
                    params=req.params or None,
                    headers=headers,
                    json=req.json_body,
                )
        except httpx.TimeoutException as exc:
            raise SuzTimeoutError(
                f"Request timed out: {req.method} {req.path}"
            ) from exc
        except httpx.RequestError as exc:
            raise SuzTransportError(
                f"Network error on {req.method} {req.path}: {exc}"
            ) from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.debug("← %d %s (%dms)", raw.status_code, req.path, elapsed_ms)

        return Response(
            status_code=raw.status_code,
            headers=dict(raw.headers),
            body=self._parse_body(raw),
        )

    def _parse_body(self, raw: httpx.Response) -> Any:
        """Parse the response body as JSON; fall back to plain text."""
        if not raw.content:
            return None
        try:
            return raw.json()
        except Exception:
            return raw.text

    def _raise_for_status(self, resp: Response, req: Request) -> None:
        """Map non-2xx responses to typed SDK exceptions.

        Attempts to extract the error message and code from the standard
        СУЗ error payload before constructing the exception.
        """
        if resp.status_code < 400:
            return

        message, error_code = self._extract_error_info(resp.body, req)

        if resp.status_code == 400:
            raise SuzValidationError(message)

        if resp.status_code == 401:
            raise SuzAuthError(message)

        if resp.status_code == 413:
            raise SuzSignatureError(
                f"HTTP 413: attached signature is not supported by the server. {message}"
            )

        # 404, 500, and anything else → SuzApiError
        raise SuzApiError(
            message=message,
            status_code=resp.status_code,
            error_code=error_code,
            raw_body=resp.body,
        )

    def _extract_error_info(self, body: Any, req: Request) -> tuple[str, str | None]:
        """Extract human-readable error message and error code from an error body.

        The СУЗ API (§6.2.1) returns errors in this shape:
            {
                "globalErrors": [{"error": "...", "errorCode": "..."}],
                "fieldErrors":  [{"fieldError": "...", "fieldName": "...", "errorCode": "..."}],
                "success": false
            }
        """
        fallback = f"HTTP {req.method} {req.path} failed"
        if not isinstance(body, dict):
            return (str(body) if body else fallback), None

        error_code: str | None = None

        # Prefer globalErrors
        global_errors = body.get("globalErrors") or []
        if global_errors and isinstance(global_errors, list):
            first = global_errors[0]
            if isinstance(first, dict):
                message = first.get("error") or fallback
                raw_code = first.get("errorCode")
                error_code = str(raw_code) if raw_code is not None else None
                return message, error_code

        # Fall back to fieldErrors
        field_errors = body.get("fieldErrors") or []
        if field_errors and isinstance(field_errors, list):
            first = field_errors[0]
            if isinstance(first, dict):
                message = first.get("fieldError") or fallback
                raw_code = first.get("errorCode")
                error_code = str(raw_code) if raw_code is not None else None
                return message, error_code

        return fallback, None

    def close(self) -> None:
        """Close the underlying httpx client and release the connection pool."""
        self._client.close()

    def __enter__(self) -> "HttpxTransport":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
