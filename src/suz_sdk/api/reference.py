"""ReferenceApi — reference data endpoints.

Endpoints implemented:
    get_providers()        GET /api/v3/providers          §4.4.x
    get_quality()          GET /api/v3/quality            §4.4.x
    get_quality_cis_list() GET /api/v3/quality/cisList    §4.4.x
    get_mod()              GET /api/v3/mod                §4.4.x
"""

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ConfigDict

from suz_sdk.transport.base import BaseTransport, Request

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ProvidersResponse(BaseModel):
    """Response model for GET /api/v3/providers.

    Attributes:
        providers: List of provider dicts (schema is product-group-specific).
    """

    providers: list[dict[str, Any]]


class QualityResponse(BaseModel):
    """Response model for GET /api/v3/quality.

    Attributes:
        order_id:      UUID of the order.
        buffer_status: Quality buffer status string.

    Any additional fields returned by the server are preserved via
    ``model_config = ConfigDict(extra="allow")``.
    """

    model_config = ConfigDict(extra="allow")

    order_id: str
    buffer_status: str


class QualityCisListResponse(BaseModel):
    """Response model for GET /api/v3/quality/cisList.

    Attributes:
        total_count: Total number of CIS items matching the query.
        results:     Page of CIS items (raw dicts; schema varies by product group).
    """

    total_count: int
    results: list[dict[str, Any]]


class ModResponse(BaseModel):
    """Response model for GET /api/v3/mod.

    Attributes:
        mod: MOD (Model of Device) identifier string.
    """

    mod: str


# ---------------------------------------------------------------------------
# Sync API class
# ---------------------------------------------------------------------------


class ReferenceApi:
    """Client for reference data endpoints.

    Instantiated and owned by SuzClient — access via ``client.reference``.

    Args:
        transport:        HTTP transport to use for requests.
        oms_id:           СУЗ instance UUID, sent as the ``omsId`` query param.
        get_auth_headers: Callable returning current authorization headers.
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

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get_providers(self) -> ProvidersResponse:
        """Retrieve the list of service providers.

        GET /api/v3/providers?omsId={omsId}

        Returns:
            ProvidersResponse with a list of provider dicts.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        req = Request(
            method="GET",
            path="/api/v3/providers",
            params={"omsId": self._oms_id},
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return ProvidersResponse(providers=body.get("providers", []))

    def get_quality(self, order_id: str) -> QualityResponse:
        """Retrieve quality buffer status for an order.

        GET /api/v3/quality?omsId={omsId}&orderId={orderId}

        Args:
            order_id: UUID of the order to query.

        Returns:
            QualityResponse with order_id, buffer_status, and any extra fields.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        req = Request(
            method="GET",
            path="/api/v3/quality",
            params={"omsId": self._oms_id, "orderId": order_id},
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return QualityResponse(
            order_id=body["orderId"],
            buffer_status=body["bufferStatus"],
            **{k: v for k, v in body.items() if k not in ("orderId", "bufferStatus")},
        )

    def get_quality_cis_list(
        self,
        order_id: str,
        gtin: str,
        limit: int | None = None,
        skip: int | None = None,
    ) -> QualityCisListResponse:
        """Retrieve a paged list of CIS quality records for an order+GTIN.

        GET /api/v3/quality/cisList?omsId={omsId}&orderId={orderId}&gtin={gtin}
                                    [&limit={limit}][&skip={skip}]

        Args:
            order_id: UUID of the order.
            gtin:     14-digit GTIN.
            limit:    Optional maximum number of records to return.
            skip:     Optional number of records to skip (offset).

        Returns:
            QualityCisListResponse with total_count and results list.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        params: dict[str, str] = {
            "omsId": self._oms_id,
            "orderId": order_id,
            "gtin": gtin,
        }
        if limit is not None:
            params["limit"] = str(limit)
        if skip is not None:
            params["skip"] = str(skip)

        req = Request(
            method="GET",
            path="/api/v3/quality/cisList",
            params=params,
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return QualityCisListResponse(
            total_count=body["totalCount"],
            results=body.get("results", []),
        )

    def get_mod(self) -> ModResponse:
        """Retrieve the MOD (Model of Device) identifier.

        GET /api/v3/mod?omsId={omsId}

        Returns:
            ModResponse with the mod string.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        req = Request(
            method="GET",
            path="/api/v3/mod",
            params={"omsId": self._oms_id},
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return ModResponse(mod=body["mod"])


# ---------------------------------------------------------------------------
# Async API class
# ---------------------------------------------------------------------------


class AsyncReferenceApi:
    """Async client for reference data endpoints.

    Instantiated and owned by AsyncSuzClient — access via ``client.reference``.

    Args:
        transport:        Async HTTP transport to use for requests.
        oms_id:           СУЗ instance UUID, sent as the ``omsId`` query param.
        get_auth_headers: Async callable returning current authorization headers.
    """

    def __init__(
        self,
        transport: object,
        oms_id: str,
        get_auth_headers: Callable[[], Awaitable[dict[str, str]]],
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._get_auth_headers = get_auth_headers

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_providers(self) -> ProvidersResponse:
        """Retrieve the list of service providers.

        GET /api/v3/providers?omsId={omsId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        req = Request(
            method="GET",
            path="/api/v3/providers",
            params={"omsId": self._oms_id},
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return ProvidersResponse(providers=body.get("providers", []))

    async def get_quality(self, order_id: str) -> QualityResponse:
        """Retrieve quality buffer status for an order.

        GET /api/v3/quality?omsId={omsId}&orderId={orderId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        req = Request(
            method="GET",
            path="/api/v3/quality",
            params={"omsId": self._oms_id, "orderId": order_id},
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return QualityResponse(
            order_id=body["orderId"],
            buffer_status=body["bufferStatus"],
            **{k: v for k, v in body.items() if k not in ("orderId", "bufferStatus")},
        )

    async def get_quality_cis_list(
        self,
        order_id: str,
        gtin: str,
        limit: int | None = None,
        skip: int | None = None,
    ) -> QualityCisListResponse:
        """Retrieve a paged list of CIS quality records for an order+GTIN.

        GET /api/v3/quality/cisList?omsId={omsId}&orderId={orderId}&gtin={gtin}
                                    [&limit={limit}][&skip={skip}]
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        params: dict[str, str] = {
            "omsId": self._oms_id,
            "orderId": order_id,
            "gtin": gtin,
        }
        if limit is not None:
            params["limit"] = str(limit)
        if skip is not None:
            params["skip"] = str(skip)

        req = Request(
            method="GET",
            path="/api/v3/quality/cisList",
            params=params,
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return QualityCisListResponse(
            total_count=body["totalCount"],
            results=body.get("results", []),
        )

    async def get_mod(self) -> ModResponse:
        """Retrieve the MOD (Model of Device) identifier.

        GET /api/v3/mod?omsId={omsId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        req = Request(
            method="GET",
            path="/api/v3/mod",
            params={"omsId": self._oms_id},
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return ModResponse(mod=body["mod"])
