"""HTTP transport layer for the SUZ SDK.

Responsibilities (§6.2 of technical spec):
- Sending HTTP requests with correct headers, timeouts, and query params
- Deserializing JSON responses
- Mapping HTTP error codes to typed SDK exceptions
- Logging request/response metadata without leaking secrets

The transport layer knows nothing about business logic, token management,
or signing.  It only moves bytes and raises exceptions.
"""

from suz_sdk.transport.base import BaseTransport, Request, Response
from suz_sdk.transport.httpx_transport import HttpxTransport

__all__ = ["BaseTransport", "Request", "Response", "HttpxTransport"]
