"""Transport Protocol and value types for the SUZ SDK.

Separating the protocol from the implementation (httpx_transport.py)
allows alternative transports (async, test doubles, etc.) to be plugged in
without touching any other SDK code.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Request:
    """Represents a single outgoing HTTP request.

    Attributes:
        method:    HTTP method string, e.g. "GET", "POST", "DELETE".
        path:      URL path relative to the transport's base_url.
                   Example: "/api/v3/ping"
        params:    Query string parameters.  Values are always strings
                   because the API only uses string query params.
        headers:   HTTP headers to send.  Transport may add its own
                   (User-Agent, Accept) but will not override caller headers.
        json_body: Python object to JSON-serialize as the request body.
                   Set to None for requests without a body (GET, DELETE).
    """

    method: str
    path: str
    params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    json_body: Any = None


@dataclass
class Response:
    """Represents a parsed HTTP response.

    Attributes:
        status_code: HTTP status code (200, 400, 500, …).
        headers:     Response headers as a plain dict (lowercase keys).
        body:        Parsed response body.  JSON is automatically parsed to
                     a dict or list; non-JSON responses yield the raw text
                     string; empty bodies yield None.
    """

    status_code: int
    headers: dict[str, str]
    body: Any


class BaseTransport(Protocol):
    """Protocol that all transport implementations must satisfy.

    The SDK interacts with HTTP exclusively through this Protocol, making it
    straightforward to swap out the underlying HTTP library (httpx → aiohttp,
    requests, …) or inject a test double.
    """

    def request(self, req: Request) -> Response:
        """Execute an HTTP request and return the parsed response.

        Args:
            req: The request to send.

        Returns:
            Parsed response.

        Raises:
            SuzTimeoutError:    Request timed out.
            SuzTransportError:  Network-level failure.
            SuzAuthError:       HTTP 401.
            SuzSignatureError:  HTTP 413 (attached signature).
            SuzApiError:        Any other non-2xx response.
        """
        ...
