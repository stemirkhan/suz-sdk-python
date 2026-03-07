"""Async httpx-based transport for the SUZ SDK."""

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

logger = logging.getLogger(__name__)

_DEFAULT_USER_AGENT = "suz-sdk-python/0.1.0"


class AsyncHttpxTransport:
    """Async HTTP transport backed by httpx.AsyncClient.

    Mirrors HttpxTransport but uses async/await.  Use as an async context
    manager or call ``aclose()`` when done.

    Args:
        base_url:   Base URL for all requests.
        timeout:    Request timeout in seconds.
        verify_ssl: Whether to verify TLS certificates.
        user_agent: Value for the User-Agent header.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        user_agent: str = _DEFAULT_USER_AGENT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            verify=verify_ssl,
        )

    async def request(self, req: Request) -> Response:
        """Execute an async HTTP request and return a parsed Response."""
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
            **req.headers,
        }

        logger.debug("→ %s %s params=%s", req.method, req.path, list(req.params.keys()))
        start = time.monotonic()

        try:
            if req.raw_body is not None:
                raw = await self._client.request(
                    method=req.method,
                    url=req.path,
                    params=req.params or None,
                    headers=headers,
                    content=req.raw_body,
                )
            else:
                raw = await self._client.request(
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

        body = self._parse_body(raw)
        resp = Response(
            status_code=raw.status_code,
            headers=dict(raw.headers),
            body=body,
        )
        self._raise_for_status(resp, req)
        return resp

    def _parse_body(self, raw: httpx.Response) -> Any:
        if not raw.content:
            return None
        try:
            return raw.json()
        except Exception:
            return raw.text

    def _raise_for_status(self, resp: Response, req: Request) -> None:
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
        raise SuzApiError(
            message=message,
            status_code=resp.status_code,
            error_code=error_code,
            raw_body=resp.body,
        )

    def _extract_error_info(self, body: Any, req: Request) -> tuple[str, str | None]:
        fallback = f"HTTP {req.method} {req.path} failed"
        if not isinstance(body, dict):
            return (str(body) if body else fallback), None
        error_code: str | None = None
        global_errors = body.get("globalErrors") or []
        if global_errors and isinstance(global_errors, list):
            first = global_errors[0]
            if isinstance(first, dict):
                message = first.get("error") or fallback
                raw_code = first.get("errorCode")
                error_code = str(raw_code) if raw_code is not None else None
                return message, error_code
        field_errors = body.get("fieldErrors") or []
        if field_errors and isinstance(field_errors, list):
            first = field_errors[0]
            if isinstance(first, dict):
                message = first.get("fieldError") or fallback
                raw_code = first.get("errorCode")
                error_code = str(raw_code) if raw_code is not None else None
                return message, error_code
        return fallback, None

    async def aclose(self) -> None:
        """Close the underlying httpx async client."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncHttpxTransport":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
