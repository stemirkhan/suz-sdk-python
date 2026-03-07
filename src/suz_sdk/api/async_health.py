"""Async HealthApi — ping endpoint (§4.2)."""

from collections.abc import Awaitable, Callable

from suz_sdk.api.health import PingResponse
from suz_sdk.transport.base import Request


class AsyncHealthApi:
    """Async client for the health check endpoint."""

    def __init__(
        self,
        transport: object,
        oms_id: str,
        get_auth_headers: Callable[[], Awaitable[dict[str, str]]],
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._get_auth_headers = get_auth_headers

    async def ping(self) -> PingResponse:
        """Check SUZ availability and retrieve version info.

        GET /api/v3/ping?omsId={omsId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        req = Request(
            method="GET",
            path="/api/v3/ping",
            params={"omsId": self._oms_id},
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body = resp.body
        return PingResponse(
            oms_id=body["omsId"],
            api_version=body["apiVersion"],
            oms_version=body["omsVersion"],
        )
