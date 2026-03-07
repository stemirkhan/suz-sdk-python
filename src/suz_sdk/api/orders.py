"""OrdersApi — KM emission orders (§4.4).

Endpoints implemented:
    create()          POST /api/v3/order              §4.4.1
    get_status()      GET  /api/v3/order/status       §4.4.2
    list_orders()     GET  /api/v3/order/list         §4.4.3
    get_codes()       GET  /api/v3/codes              §4.4.4
    get_blocks()      GET  /api/v3/order/codes/blocks §4.4.5
    get_codes_retry() GET  /api/v3/order/codes/retry  §4.4.6
    get_product_info()GET  /api/v3/order/product      §4.4.7
    close()           POST /api/v3/order/close        §4.4.8
    search_orders()   POST /api/v3/orders/search      §4.4.29

Typical flow:
    1. order = client.orders.create(product_group="...", products=[...])
    2. Poll client.orders.get_status(order.order_id) until all buffers
       have buffer_status == "ACTIVE".
    3. For each GTIN: client.orders.get_codes(order.order_id, gtin, quantity)
    4. client.orders.close(order.order_id)
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.base import BaseTransport, Request

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


@dataclass
class OrderProduct:
    """Single product line within a KM emission order (§4.4.1, Table 8)."""

    gtin: str                              # 14-digit GTIN
    quantity: int                          # int32, max 2 000 000
    serial_number_type: str                # OPERATOR | SELF_MADE | CRYPTO_CODE …
    template_id: int                       # int32, see §5.3.1.4
    cis_type: str                          # UNIT | BUNDLE | BOX …
    serial_numbers: list[str] | None = None   # only for SELF_MADE
    attributes: dict[str, Any] | None = None  # product-group-specific fields


@dataclass
class CreateOrderResponse:
    """Response from POST /api/v3/order (§4.4.1.2, Table 76)."""

    oms_id: str
    order_id: str
    expected_complete_timestamp: int   # milliseconds until ready


@dataclass
class BufferInfo:
    """Status of one KM buffer / sub-order (§4.4.2.2, Table 80)."""

    gtin: str
    buffer_status: str          # ACTIVE | PENDING | REJECTED
    available_codes: int
    total_codes: int
    total_passed: int
    unavailable_codes: int
    left_in_buffer: int
    pools_exhausted: bool
    template_id: int
    oms_id: str | None = None
    order_id: str | None = None
    rejection_reason: str | None = None
    expired_date: int | None = None          # Unix ms
    production_order_id: str | None = None
    cis_type: str | None = None


@dataclass
class GetCodesResponse:
    """Response from GET /api/v3/codes (§4.4.4.2, Table 89)."""

    oms_id: str
    codes: list[str]
    block_id: str


@dataclass
class Block:
    """A single delivery block (§4.4.5.2)."""

    block_id: str
    block_date_time: int   # Unix ms
    quantity: int


@dataclass
class GetBlocksResponse:
    """Response from GET /api/v3/order/codes/blocks (§4.4.5.2)."""

    oms_id: str
    order_id: str
    gtin: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class OrderSummaryInfo:
    """Summary of an order as returned by list_orders / search_orders (§4.4.3, §4.4.29)."""

    order_id: str
    order_status: str
    created_timestamp: int
    product_group: str | None = None
    buffers: list[BufferInfo] = field(default_factory=list)
    decline_reason: str | None = None
    production_order_id: str | None = None
    service_provider_id: str | None = None
    payment_type: int | None = None


@dataclass
class ListOrdersResponse:
    """Response from GET /api/v3/order/list (§4.4.3)."""

    oms_id: str
    order_infos: list[OrderSummaryInfo] = field(default_factory=list)


@dataclass
class OrderFilter:
    """Filter parameters for search_orders (§4.4.29)."""

    start_created_timestamp: int | None = None
    end_created_timestamp: int | None = None
    order_statuses: list[str] | None = None
    product_groups: list[str] | None = None
    production_order_ids: list[str] | None = None
    service_provider_ids: list[str] | None = None
    order_ids: list[str] | None = None


@dataclass
class SearchOrdersResponse:
    """Response from POST /api/v3/orders/search (§4.4.29)."""

    total_count: int
    results: list[OrderSummaryInfo] = field(default_factory=list)


@dataclass
class CloseOrderResponse:
    """Response from POST /api/v3/order/close (§4.4.8.2, Table 107)."""

    oms_id: str


# ---------------------------------------------------------------------------
# API class
# ---------------------------------------------------------------------------


class OrdersApi:
    """Client for KM emission order operations (§4.4).

    Args:
        transport:         HTTP transport.
        oms_id:            СУЗ instance UUID (injected as omsId query param).
        get_auth_headers:  Callable that returns current auth headers
                           (clientToken).  Provided by SuzClient.
        signer:            Optional signer for X-Signature header.
                           Required for create() and close() on all TGs
                           except pharmaceuticals.
    """

    def __init__(
        self,
        transport: BaseTransport,
        oms_id: str,
        get_auth_headers: Callable[[], dict[str, str]],
        signer: BaseSigner | None = None,
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._get_auth_headers = get_auth_headers
        self._signer = signer

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def create(
        self,
        product_group: str,
        products: list[OrderProduct],
        service_provider_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> CreateOrderResponse:
        """Create a KM emission order.

        POST /api/v3/order?omsId={omsId}

        The body is JSON-serialised, signed (X-Signature, detached CMS
        Base64) when a signer is provided, and sent verbatim so the
        signature covers the exact bytes on the wire.

        Args:
            product_group:       Product group code (e.g. "milk", "shoes").
            products:            List of OrderProduct items.
            service_provider_id: Optional UUID of the service provider.
            attributes:          Optional product-group-specific attributes.

        Returns:
            CreateOrderResponse with orderId and expectedCompleteTimestamp.
        """
        body_dict: dict[str, Any] = {
            "productGroup": product_group,
            "products": [self._product_to_dict(p) for p in products],
        }
        if service_provider_id is not None:
            body_dict["serviceProviderId"] = service_provider_id
        if attributes is not None:
            body_dict["attributes"] = attributes

        raw_body = json.dumps(body_dict, ensure_ascii=False).encode()

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._get_auth_headers(),
        }
        if self._signer is not None:
            headers["X-Signature"] = self._signer.sign_bytes(raw_body)

        req = Request(
            method="POST",
            path="/api/v3/order",
            params={"omsId": self._oms_id},
            headers=headers,
            raw_body=raw_body,
        )
        resp = self._transport.request(req)
        body = resp.body
        return CreateOrderResponse(
            oms_id=body["omsId"],
            order_id=body["orderId"],
            expected_complete_timestamp=body["expectedCompleteTimestamp"],
        )

    def get_status(
        self,
        order_id: str,
        gtin: str | None = None,
    ) -> list[BufferInfo]:
        """Get the buffer status for a KM order.

        GET /api/v3/order/status?omsId={omsId}&orderId={orderId}[&gtin={gtin}]

        Poll until every BufferInfo.buffer_status == "ACTIVE" before
        calling get_codes().  A status of "REJECTED" means the order was
        declined; check rejection_reason.

        Args:
            order_id: UUID returned by create().
            gtin:     Optional 14-digit GTIN to query a single sub-order.

        Returns:
            List of BufferInfo objects (one per GTIN in the order).
        """
        params: dict[str, str] = {
            "omsId": self._oms_id,
            "orderId": order_id,
        }
        if gtin is not None:
            params["gtin"] = gtin

        req = Request(
            method="GET",
            path="/api/v3/order/status",
            params=params,
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        return [self._parse_buffer_info(item) for item in resp.body]

    def list_orders(self) -> ListOrdersResponse:
        """List all KM emission orders for the OMS instance.

        GET /api/v3/order/list?omsId={omsId}

        Returns:
            ListOrdersResponse containing omsId and a list of OrderSummaryInfo.
        """
        req = Request(
            method="GET",
            path="/api/v3/order/list",
            params={"omsId": self._oms_id},
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body = resp.body
        return ListOrdersResponse(
            oms_id=body["omsId"],
            order_infos=[
                self._parse_order_summary_info(item) for item in body.get("orderInfos", [])
            ],
        )

    def get_codes(
        self,
        order_id: str,
        gtin: str,
        quantity: int,
    ) -> GetCodesResponse:
        """Fetch a block of KM codes from an active order.

        GET /api/v3/codes?omsId={omsId}&orderId={orderId}&quantity={quantity}&gtin={gtin}

        quantity must not exceed 150 000.  The returned block_id identifies
        this delivery block.  Call repeatedly with the desired quantity until
        all codes are fetched.

        Args:
            order_id: UUID returned by create().
            gtin:     14-digit GTIN to fetch codes for.
            quantity: Number of codes to fetch (≤ 150 000).

        Returns:
            GetCodesResponse with codes list and block_id.
        """
        req = Request(
            method="GET",
            path="/api/v3/codes",
            params={
                "omsId": self._oms_id,
                "orderId": order_id,
                "quantity": str(quantity),
                "gtin": gtin,
            },
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body = resp.body
        return GetCodesResponse(
            oms_id=body["omsId"],
            codes=body["codes"],
            block_id=body["blockId"],
        )

    def get_blocks(
        self,
        order_id: str,
        gtin: str,
    ) -> GetBlocksResponse:
        """Get the list of delivered code blocks for an order+GTIN.

        GET /api/v3/order/codes/blocks?omsId={omsId}&orderId={orderId}&gtin={gtin}

        Args:
            order_id: UUID of the order.
            gtin:     14-digit GTIN.

        Returns:
            GetBlocksResponse with a list of Block objects.
        """
        req = Request(
            method="GET",
            path="/api/v3/order/codes/blocks",
            params={
                "omsId": self._oms_id,
                "orderId": order_id,
                "gtin": gtin,
            },
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body = resp.body
        return GetBlocksResponse(
            oms_id=body["omsId"],
            order_id=body["orderId"],
            gtin=body["gtin"],
            blocks=[
                Block(
                    block_id=b["blockId"],
                    block_date_time=b["blockDateTime"],
                    quantity=b["quantity"],
                )
                for b in body.get("blocks", [])
            ],
        )

    def get_codes_retry(self, block_id: str) -> GetCodesResponse:
        """Retry fetching a previously issued block of KM codes.

        GET /api/v3/order/codes/retry?omsId={omsId}&blockId={blockId}

        Use this when a get_codes() call was successful on the server side
        but the response was not received (e.g. network error).

        Args:
            block_id: The blockId returned by the original get_codes() call.

        Returns:
            GetCodesResponse identical to the original get_codes() response.
        """
        req = Request(
            method="GET",
            path="/api/v3/order/codes/retry",
            params={
                "omsId": self._oms_id,
                "blockId": block_id,
            },
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        body = resp.body
        return GetCodesResponse(
            oms_id=body["omsId"],
            codes=body["codes"],
            block_id=body["blockId"],
        )

    def get_product_info(self, order_id: str) -> dict[str, dict[str, Any]]:
        """Get product attribute info for all GTINs in an order.

        GET /api/v3/order/product?omsId={omsId}&orderId={orderId}

        Returns a free-form dict keyed by GTIN, where each value is a dict
        of attribute name → attribute value specific to the product group.

        Args:
            order_id: UUID of the order.

        Returns:
            dict mapping GTIN string to a dict of product attributes.
        """
        req = Request(
            method="GET",
            path="/api/v3/order/product",
            params={
                "omsId": self._oms_id,
                "orderId": order_id,
            },
            headers={
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
        )
        resp = self._transport.request(req)
        return cast(dict[str, dict[str, Any]], resp.body)

    def search_orders(
        self,
        filter: OrderFilter | None = None,
        limit: int = 10,
        page: int = 0,
    ) -> SearchOrdersResponse:
        """Search orders with optional filtering and pagination.

        POST /api/v3/orders/search?omsId={omsId}

        Args:
            filter: Optional OrderFilter with search criteria.
            limit:  Maximum number of results to return.
            page:   Zero-based page number.

        Returns:
            SearchOrdersResponse with total_count and a list of OrderSummaryInfo.
        """
        body_dict: dict[str, Any] = {
            "filter": self._order_filter_to_dict(filter) if filter else {},
            "limit": limit,
            "page": page,
        }
        req = Request(
            method="POST",
            path="/api/v3/orders/search",
            params={"omsId": self._oms_id},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                **self._get_auth_headers(),
            },
            json_body=body_dict,
        )
        resp = self._transport.request(req)
        body = resp.body
        return SearchOrdersResponse(
            total_count=body["totalCount"],
            results=[self._parse_order_summary_info(item) for item in body.get("results", [])],
        )

    def close(
        self,
        order_id: str,
        gtin: str | None = None,
    ) -> CloseOrderResponse:
        """Close a KM order (or a single sub-order by GTIN).

        POST /api/v3/order/close?omsId={omsId}

        If gtin is omitted, all sub-orders of the order are closed.
        The body is signed with X-Signature when a signer is configured.

        Args:
            order_id: UUID returned by create().
            gtin:     Optional 14-digit GTIN.  Omit to close all sub-orders.

        Returns:
            CloseOrderResponse containing omsId.
        """
        body_dict: dict[str, Any] = {"orderId": order_id}
        if gtin is not None:
            body_dict["gtin"] = gtin

        raw_body = json.dumps(body_dict, ensure_ascii=False).encode()

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._get_auth_headers(),
        }
        if self._signer is not None:
            headers["X-Signature"] = self._signer.sign_bytes(raw_body)

        req = Request(
            method="POST",
            path="/api/v3/order/close",
            params={"omsId": self._oms_id},
            headers=headers,
            raw_body=raw_body,
        )
        resp = self._transport.request(req)
        return CloseOrderResponse(oms_id=resp.body["omsId"])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _product_to_dict(product: OrderProduct) -> dict[str, Any]:
        d: dict[str, Any] = {
            "gtin": product.gtin,
            "quantity": product.quantity,
            "serialNumberType": product.serial_number_type,
            "templateId": product.template_id,
            "cisType": product.cis_type,
        }
        if product.serial_numbers is not None:
            d["serialNumbers"] = product.serial_numbers
        if product.attributes is not None:
            d["attributes"] = product.attributes
        return d

    @staticmethod
    def _parse_buffer_info(data: dict[str, Any]) -> BufferInfo:
        return BufferInfo(
            gtin=data["gtin"],
            buffer_status=data["bufferStatus"],
            available_codes=data.get("availableCodes", 0),
            total_codes=data["totalCodes"],
            total_passed=data.get("totalPassed", 0),
            unavailable_codes=data.get("unavailableCodes", 0),
            left_in_buffer=data.get("leftInBuffer", 0),
            pools_exhausted=data.get("poolsExhausted", False),
            template_id=data.get("templateId", 0),
            oms_id=data.get("omsId"),
            order_id=data.get("orderId"),
            rejection_reason=data.get("rejectionReason"),
            expired_date=data.get("expiredDate"),
            production_order_id=data.get("productionOrderId"),
            cis_type=data.get("cisType"),
        )

    @staticmethod
    def _parse_order_summary_info(data: dict[str, Any]) -> OrderSummaryInfo:
        return OrderSummaryInfo(
            order_id=data["orderId"],
            order_status=data["orderStatus"],
            created_timestamp=data["createdTimestamp"],
            product_group=data.get("productGroup"),
            buffers=[OrdersApi._parse_buffer_info(b) for b in data.get("buffers", [])],
            decline_reason=data.get("declineReason"),
            production_order_id=data.get("productionOrderId"),
            service_provider_id=data.get("serviceProviderId"),
            payment_type=data.get("paymentType"),
        )

    @staticmethod
    def _order_filter_to_dict(f: OrderFilter) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if f.start_created_timestamp is not None:
            d["startCreatedTimestamp"] = f.start_created_timestamp
        if f.end_created_timestamp is not None:
            d["endCreatedTimestamp"] = f.end_created_timestamp
        if f.order_statuses is not None:
            d["orderStatuses"] = f.order_statuses
        if f.product_groups is not None:
            d["productGroups"] = f.product_groups
        if f.production_order_ids is not None:
            d["productionOrderIds"] = f.production_order_ids
        if f.service_provider_ids is not None:
            d["serviceProviderIds"] = f.service_provider_ids
        if f.order_ids is not None:
            d["orderIds"] = f.order_ids
        return d
