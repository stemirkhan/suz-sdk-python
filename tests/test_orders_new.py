"""Tests for new OrdersApi methods (§4.4): list_orders, get_blocks, get_codes_retry,
get_product_info, search_orders.
"""

import pytest

from suz_sdk.api.orders import (
    Block,
    BufferInfo,
    GetBlocksResponse,
    GetCodesResponse,
    ListOrdersResponse,
    OrderFilter,
    OrderSummaryInfo,
    OrdersApi,
    SearchOrdersResponse,
)
from suz_sdk.transport.base import Request, Response


_OMS_ID = "cdf12109-10d3-11e6-8b6f-0050569977a1"
_ORDER_ID = "b024ae09-ef7c-449e-b461-05d8eb116c79"
_GTIN = "01334567894339"
_BLOCK_ID = "012cc7b0-c9e4-4511-8058-2de1f97a87b0"
_OMS_CONNECTION = "aabb1234-5678-90ab-cdef-1234567890ab"


class StubTransport:
    def __init__(self, response: Response | None = None, exc: Exception | None = None) -> None:
        self._response = response
        self._exc = exc
        self.last_request: Request | None = None

    def request(self, req: Request) -> Response:
        self.last_request = req
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


def _make_api(transport: StubTransport) -> OrdersApi:
    return OrdersApi(
        transport=transport,
        oms_id=_OMS_ID,
        get_auth_headers=lambda: {"clientToken": "tok"},
    )


_SUMMARY_INFO = {
    "orderId": _ORDER_ID,
    "orderStatus": "ACTIVE",
    "createdTimestamp": 1700000000000,
    "productGroup": "milk",
    "buffers": [],
    "declineReason": None,
    "productionOrderId": None,
    "serviceProviderId": None,
    "paymentType": None,
}

_LIST_ORDERS_RESP = {
    "omsId": _OMS_ID,
    "orderInfos": [_SUMMARY_INFO],
}

_BLOCKS_RESP = {
    "omsId": _OMS_ID,
    "orderId": _ORDER_ID,
    "gtin": _GTIN,
    "blocks": [
        {"blockId": _BLOCK_ID, "blockDateTime": 1700000000000, "quantity": 10},
    ],
}

_RETRY_RESP = {
    "omsId": _OMS_ID,
    "codes": ["code-retry-1", "code-retry-2"],
    "blockId": _BLOCK_ID,
}

_PRODUCT_INFO_RESP = {
    _GTIN: {"attr1": "value1", "attr2": "value2"},
}

_SEARCH_RESP = {
    "totalCount": 1,
    "results": [_SUMMARY_INFO],
}


# ---------------------------------------------------------------------------
# list_orders()
# ---------------------------------------------------------------------------

class TestListOrders:
    def test_returns_response_model(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_ORDERS_RESP,
        ))
        result = _make_api(transport).list_orders()

        assert isinstance(result, ListOrdersResponse)
        assert result.oms_id == _OMS_ID

    def test_parses_order_infos(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_ORDERS_RESP,
        ))
        result = _make_api(transport).list_orders()

        assert len(result.order_infos) == 1
        info = result.order_infos[0]
        assert isinstance(info, OrderSummaryInfo)
        assert info.order_id == _ORDER_ID
        assert info.order_status == "ACTIVE"
        assert info.created_timestamp == 1700000000000
        assert info.product_group == "milk"
        assert info.buffers == []

    def test_empty_order_infos_when_missing(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body={"omsId": _OMS_ID},
        ))
        result = _make_api(transport).list_orders()

        assert result.order_infos == []

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_ORDERS_RESP,
        ))
        _make_api(transport).list_orders()

        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/order/list"

    def test_sends_oms_id_as_query_param(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_ORDERS_RESP,
        ))
        _make_api(transport).list_orders()

        assert transport.last_request is not None
        assert transport.last_request.params.get("omsId") == _OMS_ID

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_ORDERS_RESP,
        ))
        _make_api(transport).list_orders()

        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == "tok"

    def test_parses_buffer_info_in_order(self) -> None:
        buffer_data = {
            "gtin": _GTIN,
            "bufferStatus": "ACTIVE",
            "totalCodes": 10,
        }
        summary = {**_SUMMARY_INFO, "buffers": [buffer_data]}
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderInfos": [summary]},
        ))
        result = _make_api(transport).list_orders()

        buf = result.order_infos[0].buffers[0]
        assert isinstance(buf, BufferInfo)
        assert buf.gtin == _GTIN
        assert buf.buffer_status == "ACTIVE"
        assert buf.available_codes == 0  # missing from data → default 0


# ---------------------------------------------------------------------------
# get_blocks()
# ---------------------------------------------------------------------------

class TestGetBlocks:
    def test_returns_response_model(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_BLOCKS_RESP,
        ))
        result = _make_api(transport).get_blocks(_ORDER_ID, _GTIN)

        assert isinstance(result, GetBlocksResponse)
        assert result.oms_id == _OMS_ID
        assert result.order_id == _ORDER_ID
        assert result.gtin == _GTIN

    def test_parses_blocks(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_BLOCKS_RESP,
        ))
        result = _make_api(transport).get_blocks(_ORDER_ID, _GTIN)

        assert len(result.blocks) == 1
        blk = result.blocks[0]
        assert isinstance(blk, Block)
        assert blk.block_id == _BLOCK_ID
        assert blk.block_date_time == 1700000000000
        assert blk.quantity == 10

    def test_empty_blocks_when_missing(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "gtin": _GTIN},
        ))
        result = _make_api(transport).get_blocks(_ORDER_ID, _GTIN)

        assert result.blocks == []

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_BLOCKS_RESP,
        ))
        _make_api(transport).get_blocks(_ORDER_ID, _GTIN)

        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/order/codes/blocks"

    def test_sends_correct_query_params(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_BLOCKS_RESP,
        ))
        _make_api(transport).get_blocks(_ORDER_ID, _GTIN)

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("orderId") == _ORDER_ID
        assert req.params.get("gtin") == _GTIN


# ---------------------------------------------------------------------------
# get_codes_retry()
# ---------------------------------------------------------------------------

class TestGetCodesRetry:
    def test_returns_response_model(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_RETRY_RESP,
        ))
        result = _make_api(transport).get_codes_retry(_BLOCK_ID)

        assert isinstance(result, GetCodesResponse)
        assert result.oms_id == _OMS_ID
        assert result.block_id == _BLOCK_ID
        assert result.codes == ["code-retry-1", "code-retry-2"]

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_RETRY_RESP,
        ))
        _make_api(transport).get_codes_retry(_BLOCK_ID)

        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/order/codes/retry"

    def test_sends_correct_query_params(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_RETRY_RESP,
        ))
        _make_api(transport).get_codes_retry(_BLOCK_ID)

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("blockId") == _BLOCK_ID


# ---------------------------------------------------------------------------
# get_product_info()
# ---------------------------------------------------------------------------

class TestGetProductInfo:
    def test_returns_dict(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_PRODUCT_INFO_RESP,
        ))
        result = _make_api(transport).get_product_info(_ORDER_ID)

        assert isinstance(result, dict)
        assert _GTIN in result
        assert result[_GTIN] == {"attr1": "value1", "attr2": "value2"}

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_PRODUCT_INFO_RESP,
        ))
        _make_api(transport).get_product_info(_ORDER_ID)

        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/order/product"

    def test_sends_correct_query_params(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_PRODUCT_INFO_RESP,
        ))
        _make_api(transport).get_product_info(_ORDER_ID)

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("orderId") == _ORDER_ID


# ---------------------------------------------------------------------------
# search_orders()
# ---------------------------------------------------------------------------

class TestSearchOrders:
    def test_returns_response_model(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_SEARCH_RESP,
        ))
        result = _make_api(transport).search_orders()

        assert isinstance(result, SearchOrdersResponse)
        assert result.total_count == 1

    def test_parses_results(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_SEARCH_RESP,
        ))
        result = _make_api(transport).search_orders()

        assert len(result.results) == 1
        info = result.results[0]
        assert isinstance(info, OrderSummaryInfo)
        assert info.order_id == _ORDER_ID

    def test_sends_post_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_SEARCH_RESP,
        ))
        _make_api(transport).search_orders()

        req = transport.last_request
        assert req is not None
        assert req.method == "POST"
        assert req.path == "/api/v3/orders/search"

    def test_sends_oms_id_as_query_param(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_SEARCH_RESP,
        ))
        _make_api(transport).search_orders()

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    def test_sends_limit_and_page_in_body(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_SEARCH_RESP,
        ))
        _make_api(transport).search_orders(limit=5, page=2)

        req = transport.last_request
        assert req is not None
        body = req.json_body
        assert body is not None
        assert body["limit"] == 5
        assert body["page"] == 2

    def test_empty_filter_when_none(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_SEARCH_RESP,
        ))
        _make_api(transport).search_orders(filter=None)

        req = transport.last_request
        assert req is not None
        body = req.json_body
        assert body is not None
        assert body["filter"] == {}

    def test_filter_fields_sent_in_body(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_SEARCH_RESP,
        ))
        f = OrderFilter(
            order_statuses=["ACTIVE"],
            order_ids=[_ORDER_ID],
            start_created_timestamp=1700000000000,
        )
        _make_api(transport).search_orders(filter=f)

        req = transport.last_request
        assert req is not None
        body = req.json_body
        assert body is not None
        filt = body["filter"]
        assert filt["orderStatuses"] == ["ACTIVE"]
        assert filt["orderIds"] == [_ORDER_ID]
        assert filt["startCreatedTimestamp"] == 1700000000000

    def test_filter_omits_none_fields(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_SEARCH_RESP,
        ))
        f = OrderFilter(order_statuses=["ACTIVE"])
        _make_api(transport).search_orders(filter=f)

        req = transport.last_request
        assert req is not None
        body = req.json_body
        assert body is not None
        filt = body["filter"]
        assert "orderIds" not in filt
        assert "productGroups" not in filt

    def test_empty_results_when_missing(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body={"totalCount": 0},
        ))
        result = _make_api(transport).search_orders()

        assert result.total_count == 0
        assert result.results == []


# ---------------------------------------------------------------------------
# _parse_buffer_info defaults (for list_orders compatibility)
# ---------------------------------------------------------------------------

class TestParseBufferInfoDefaults:
    """Verify _parse_buffer_info uses safe defaults for fields missing in list_orders."""

    def test_missing_available_codes_defaults_to_zero(self) -> None:
        data = {"gtin": _GTIN, "bufferStatus": "ACTIVE", "totalCodes": 10}
        buf = OrdersApi._parse_buffer_info(data)
        assert buf.available_codes == 0

    def test_missing_total_passed_defaults_to_zero(self) -> None:
        data = {"gtin": _GTIN, "bufferStatus": "ACTIVE", "totalCodes": 10}
        buf = OrdersApi._parse_buffer_info(data)
        assert buf.total_passed == 0

    def test_missing_pools_exhausted_defaults_to_false(self) -> None:
        data = {"gtin": _GTIN, "bufferStatus": "ACTIVE", "totalCodes": 10}
        buf = OrdersApi._parse_buffer_info(data)
        assert buf.pools_exhausted is False

    def test_missing_template_id_defaults_to_zero(self) -> None:
        data = {"gtin": _GTIN, "bufferStatus": "ACTIVE", "totalCodes": 10}
        buf = OrdersApi._parse_buffer_info(data)
        assert buf.template_id == 0
