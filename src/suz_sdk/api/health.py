"""Health check API client (§4.4.25).

Implements the "Проверить доступность СУЗ" (Check СУЗ availability) method.

API specification (§4.4.25):
    Method:  GET
    URL:     <base_url>/api/v3/ping?omsId={omsId}
    Headers:
        Accept:      application/json        (required)
        clientToken: {token}                 (required, unless using Authorization)
        Authorization: token {token_id}      (alternative, pharmaceuticals only)

    Response 200:
        {
            "omsId":      "cdf12109-10d3-11e6-8b6f-0050569977a1",
            "apiVersion": "2.0.0.54",
            "omsVersion": "3.1.8.0"
        }
"""

from collections.abc import Callable

from pydantic import BaseModel

from suz_sdk.transport.base import BaseTransport, Request


class PingResponse(BaseModel):
    """Response model for the ping endpoint (§4.4.25, Table 237).

    Attributes:
        oms_id:      Unique identifier of the СУЗ instance.
        api_version: СУЗ API version string (e.g. "2.0.0.54").
        oms_version: СУЗ software version string (e.g. "3.1.8.0").
    """

    oms_id: str
    api_version: str
    oms_version: str


class HealthApi:
    """Client for the СУЗ health / availability endpoint.

    Instantiated and owned by SuzClient — callers access it via
    ``client.health``.

    Args:
        transport:        HTTP transport to use for requests.
        oms_id:           СУЗ instance UUID, sent as the `omsId` query param.
        get_auth_headers: Callable that returns the current authorization
                          headers (clientToken or Authorization).  This
                          indirection allows SuzClient to swap in a
                          TokenManager in future iterations without changing
                          this class.
    """

    def __init__(
        self,
        transport: BaseTransport,
        oms_id: str,
        get_auth_headers: Callable[[], dict[str, str]],
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._get_auth_headers = get_auth_headers

    def ping(self) -> PingResponse:
        """Check СУЗ availability and retrieve version information.

        Sends GET /api/v3/ping?omsId={omsId} with the current clientToken.

        Returns:
            PingResponse with omsId, apiVersion, and omsVersion.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        req = Request(
            method="GET",
            path="/api/v3/ping",
            params={"omsId": self._oms_id},
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)

        # Defensive: body is guaranteed non-None here because the transport
        # raises on non-2xx, and a 200 ping always returns JSON.
        body: dict[str, str] = resp.body  # type: ignore[assignment]
        return PingResponse(
            oms_id=body["omsId"],
            api_version=body["apiVersion"],
            oms_version=body["omsVersion"],
        )
