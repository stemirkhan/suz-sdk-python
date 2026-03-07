"""Async OrdersApi — KM emission orders (§4.4)."""

import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

from suz_sdk.api.orders import (
    Block,
    BufferInfo,
    CloseOrderResponse,
    CreateOrderResponse,
    GetBlocksResponse,
    GetCodesResponse,
    ListOrdersResponse,
    OrderFilter,
    OrderProduct,
    OrdersApi,
    OrderSummaryInfo,
    SearchOrdersResponse,
)
from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.base import Request


class AsyncOrdersApi:
    """Async client for KM emission order operations (§4.4)."""

    def __init__(
        self,
        transport: object,
        oms_id: str,
        get_auth_headers: Callable[[], Awaitable[dict[str, str]]],
        signer: BaseSigner | None = None,
    ) -> None:
        self._transport = transport
        self._oms_id = oms_id
        self._get_auth_headers = get_auth_headers
        self._signer = signer

    async def create(
        self,
        product_group: str,
        products: list[OrderProduct],
        service_provider_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> CreateOrderResponse:
        """Create a KM emission order (POST /api/v3/order)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        body_dict: dict[str, Any] = {
            "productGroup": product_group,
            "products": [OrdersApi._product_to_dict(p) for p in products],
        }
        if service_provider_id is not None:
            body_dict["serviceProviderId"] = service_provider_id
        if attributes is not None:
            body_dict["attributes"] = attributes

        raw_body = json.dumps(body_dict, ensure_ascii=False).encode()

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(await self._get_auth_headers()),
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
        resp = await transport.request(req)
        body = resp.body
        return CreateOrderResponse(
            oms_id=body["omsId"],
            order_id=body["orderId"],
            expected_complete_timestamp=body["expectedCompleteTimestamp"],
        )

    async def get_status(
        self,
        order_id: str,
        gtin: str | None = None,
    ) -> list[BufferInfo]:
        """Get buffer status for a KM order (GET /api/v3/order/status)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        params: dict[str, str] = {"omsId": self._oms_id, "orderId": order_id}
        if gtin is not None:
            params["gtin"] = gtin

        req = Request(
            method="GET",
            path="/api/v3/order/status",
            params=params,
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        return [OrdersApi._parse_buffer_info(item) for item in resp.body]

    async def list_orders(self) -> ListOrdersResponse:
        """List all KM emission orders (GET /api/v3/order/list)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        req = Request(
            method="GET",
            path="/api/v3/order/list",
            params={"omsId": self._oms_id},
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body = resp.body
        return ListOrdersResponse(
            oms_id=body["omsId"],
            order_infos=[
                OrdersApi._parse_order_summary_info(item)
                for item in body.get("orderInfos", [])
            ],
        )

    async def get_codes(
        self,
        order_id: str,
        gtin: str,
        quantity: int,
    ) -> GetCodesResponse:
        """Fetch a block of KM codes (GET /api/v3/codes)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

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
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body = resp.body
        return GetCodesResponse(
            oms_id=body["omsId"],
            codes=body["codes"],
            block_id=body["blockId"],
        )

    async def get_blocks(
        self,
        order_id: str,
        gtin: str,
    ) -> GetBlocksResponse:
        """Get delivered code blocks for an order+GTIN (GET /api/v3/order/codes/blocks)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

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
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
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

    async def get_codes_retry(self, block_id: str) -> GetCodesResponse:
        """Retry fetching a previously issued block of codes (GET /api/v3/order/codes/retry)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        req = Request(
            method="GET",
            path="/api/v3/order/codes/retry",
            params={
                "omsId": self._oms_id,
                "blockId": block_id,
            },
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        body = resp.body
        return GetCodesResponse(
            oms_id=body["omsId"],
            codes=body["codes"],
            block_id=body["blockId"],
        )

    async def get_product_info(self, order_id: str) -> dict[str, dict[str, Any]]:
        """Get product attribute info for all GTINs in an order (GET /api/v3/order/product)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        req = Request(
            method="GET",
            path="/api/v3/order/product",
            params={
                "omsId": self._oms_id,
                "orderId": order_id,
            },
            headers={
                "Accept": "application/json",
                **(await self._get_auth_headers()),
            },
        )
        resp = await transport.request(req)
        return cast(dict[str, dict[str, Any]], resp.body)

    async def search_orders(
        self,
        filter: OrderFilter | None = None,
        limit: int = 10,
        page: int = 0,
    ) -> SearchOrdersResponse:
        """Search orders with filtering and pagination (POST /api/v3/orders/search)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        body_dict: dict[str, Any] = {
            "filter": OrdersApi._order_filter_to_dict(filter) if filter else {},
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
                **(await self._get_auth_headers()),
            },
            json_body=body_dict,
        )
        resp = await transport.request(req)
        body = resp.body
        return SearchOrdersResponse(
            total_count=body["totalCount"],
            results=[
                OrdersApi._parse_order_summary_info(item)
                for item in body.get("results", [])
            ],
        )

    async def close(
        self,
        order_id: str,
        gtin: str | None = None,
    ) -> CloseOrderResponse:
        """Close a KM order (POST /api/v3/order/close)."""
        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        transport: AsyncHttpxTransport = self._transport  # type: ignore[assignment]

        body_dict: dict[str, Any] = {"orderId": order_id}
        if gtin is not None:
            body_dict["gtin"] = gtin

        raw_body = json.dumps(body_dict, ensure_ascii=False).encode()

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **(await self._get_auth_headers()),
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
        resp = await transport.request(req)
        return CloseOrderResponse(oms_id=resp.body["omsId"])


# Re-export for convenience
__all__ = [
    "AsyncOrdersApi",
    "Block",
    "BufferInfo",
    "CloseOrderResponse",
    "CreateOrderResponse",
    "GetBlocksResponse",
    "GetCodesResponse",
    "ListOrdersResponse",
    "OrderFilter",
    "OrderProduct",
    "OrderSummaryInfo",
    "SearchOrdersResponse",
]
