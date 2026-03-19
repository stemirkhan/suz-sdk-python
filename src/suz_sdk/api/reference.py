"""ReferenceApi — reference data endpoints.

Endpoints implemented:
    get_providers()        GET /api/v3/providers          §4.4.x
    get_quality()          GET /api/v3/quality            §4.4.x
    get_quality_cis_list() GET /api/v3/quality/cisList    §4.4.x
    get_mod()              GET /api/v3/mod                §4.4.x
"""

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

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


class QualityListResponse(BaseModel):
    """Response model for GET /api/v3/quality (§4.4.15, Table 189).

    Returns a list of utilisation report IDs (not quality status details).

    Attributes:
        total_count: Total number of matching report IDs.
        results:     List of report UUID strings.
    """

    total_count: int
    results: list[str]


class QualityCisListResponse(BaseModel):
    """Response model for GET /api/v3/quality/cisList (§4.4.16, Table 193).

    Attributes:
        sntins:     List of IdentificationCode objects with ``code`` and optional
                    ``quality`` fields.
        usage_type: Usage type — ``PRINTED`` or ``VERIFIED``.
        order_id:   Order UUID (optional).
    """

    sntins: list[dict[str, Any]]
    usage_type: str
    order_id: str | None = None


class ModListResponse(BaseModel):
    """Response model for GET /api/v3/mod (§4.4.17, Table 198).

    Attributes:
        total_count:      Total number of MOD records matching the query.
        manufacture_info: List of manufactureInfo objects (Table 199).
    """

    total_count: int
    manufacture_info: list[dict[str, Any]]


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

    def get_quality(
        self,
        order_id: str | None = None,
        limit: int | None = None,
        skip: int | None = None,
    ) -> QualityListResponse:
        """Retrieve list of utilisation report IDs ("Сведения о нанесении").

        GET /api/v3/quality?omsId={omsId}[&orderId={orderId}][&limit={limit}][&skip={skip}]

        Returns a paginated list of report UUID strings (§4.4.15, Table 189).

        Args:
            order_id: Optional UUID of the order to filter by.
            limit:    Max records to return (default 10, max 100).
            skip:     Page offset (default 1).

        Returns:
            QualityListResponse with total_count and list of report ID strings.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        params: dict[str, str] = {"omsId": self._oms_id}
        if order_id is not None:
            params["orderId"] = order_id
        if limit is not None:
            params["limit"] = str(limit)
        if skip is not None:
            params["skip"] = str(skip)

        req = Request(
            method="GET",
            path="/api/v3/quality",
            params=params,
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return QualityListResponse(
            total_count=body["totalCount"],
            results=body.get("results") or [],
        )

    def get_quality_cis_list(
        self,
        report_id: str,
    ) -> QualityCisListResponse:
        """Retrieve KI list from a "Сведения о нанесении" report.

        GET /api/v3/quality/cisList?omsId={omsId}&reportId={reportId}

        Returns KM codes (without verification code) with print quality class
        for each code in the given utilisation report (§4.4.16, Table 193).

        Args:
            report_id: UUID of the utilisation report obtained from
                       ``get_quality()`` (§4.4.15).

        Returns:
            QualityCisListResponse with sntins list, usage_type, and order_id.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        req = Request(
            method="GET",
            path="/api/v3/quality/cisList",
            params={"omsId": self._oms_id, "reportId": report_id},
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return QualityCisListResponse(
            sntins=body.get("sntins") or [],
            usage_type=body["usageType"],
            order_id=body.get("orderId"),
        )

    def get_mod(
        self,
        product_group: str,
        limit: int | None = None,
        skip: int | None = None,
    ) -> ModListResponse:
        """Retrieve places of business activity (MOD — места осуществления деятельности).

        GET /api/v3/mod?omsId={omsId}&productGroup={productGroup}
                        [&limit={limit}][&skip={skip}]

        Available for specific product groups only (§4.4.17, Table 195).

        Args:
            product_group: Product group code (required).
            limit:         Max records to return (default 10, max 1000).
            skip:          Zero-based index of first record to return.

        Returns:
            ModListResponse with total_count and manufacture_info list.

        Raises:
            SuzAuthError:       clientToken is missing or invalid.
            SuzTransportError:  Network-level failure.
            SuzTimeoutError:    Request timed out.
            SuzApiError:        Unexpected server error.
        """
        params: dict[str, str] = {
            "omsId": self._oms_id,
            "productGroup": product_group,
        }
        if limit is not None:
            params["limit"] = str(limit)
        if skip is not None:
            params["skip"] = str(skip)

        req = Request(
            method="GET",
            path="/api/v3/mod",
            params=params,
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body: dict[str, Any] = resp.body
        return ModListResponse(
            total_count=body["totalCount"],
            manufacture_info=body.get("manufactureInfo") or [],
        )


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

    async def get_quality(
        self,
        order_id: str | None = None,
        limit: int | None = None,
        skip: int | None = None,
    ) -> QualityListResponse:
        """Retrieve list of utilisation report IDs (§4.4.15).

        GET /api/v3/quality?omsId={omsId}[&orderId={orderId}][&limit={limit}][&skip={skip}]
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        params: dict[str, str] = {"omsId": self._oms_id}
        if order_id is not None:
            params["orderId"] = order_id
        if limit is not None:
            params["limit"] = str(limit)
        if skip is not None:
            params["skip"] = str(skip)

        req = Request(
            method="GET",
            path="/api/v3/quality",
            params=params,
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return QualityListResponse(
            total_count=body["totalCount"],
            results=body.get("results") or [],
        )

    async def get_quality_cis_list(
        self,
        report_id: str,
    ) -> QualityCisListResponse:
        """Retrieve KI list from a utilisation report (§4.4.16).

        GET /api/v3/quality/cisList?omsId={omsId}&reportId={reportId}
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        req = Request(
            method="GET",
            path="/api/v3/quality/cisList",
            params={"omsId": self._oms_id, "reportId": report_id},
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return QualityCisListResponse(
            sntins=body.get("sntins") or [],
            usage_type=body["usageType"],
            order_id=body.get("orderId"),
        )

    async def get_mod(
        self,
        product_group: str,
        limit: int | None = None,
        skip: int | None = None,
    ) -> ModListResponse:
        """Retrieve places of business activity (§4.4.17).

        GET /api/v3/mod?omsId={omsId}&productGroup={productGroup}
                        [&limit={limit}][&skip={skip}]
        """
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]
        params: dict[str, str] = {
            "omsId": self._oms_id,
            "productGroup": product_group,
        }
        if limit is not None:
            params["limit"] = str(limit)
        if skip is not None:
            params["skip"] = str(skip)

        req = Request(
            method="GET",
            path="/api/v3/mod",
            params=params,
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body: dict[str, Any] = resp.body
        return ModListResponse(
            total_count=body["totalCount"],
            manufacture_info=body.get("manufactureInfo") or [],
        )
