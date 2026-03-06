"""Tests for OrdersApi (§4.4): create, get_status, get_codes, close."""

import json

import pytest

from suz_sdk.api.orders import (
    BufferInfo,
    CloseOrderResponse,
    CreateOrderResponse,
    GetCodesResponse,
    OrderProduct,
    OrdersApi,
)
from suz_sdk.signing.noop import NoopSigner
from suz_sdk.transport.base import Request, Response


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_OMS_ID = "cdf12109-10d3-11e6-8b6f-0050569977a1"
_ORDER_ID = "b024ae09-ef7c-449e-b461-05d8eb116c79"
_GTIN = "01334567894339"
_BLOCK_ID = "012cc7b0-c9e4-4511-8058-2de1f97a87b0"

_PRODUCT = OrderProduct(
    gtin=_GTIN,
    quantity=20,
    serial_number_type="OPERATOR",
    template_id=50,
    cis_type="UNIT",
)

_ACTIVE_BUFFER = {
    "omsId": _OMS_ID,
    "orderId": _ORDER_ID,
    "leftInBuffer": 0,
    "totalCodes": 20,
    "poolsExhausted": False,
    "unavailableCodes": 0,
    "availableCodes": 20,
    "gtin": _GTIN,
    "bufferStatus": "ACTIVE",
    "totalPassed": 0,
    "expiredDate": 1596792681987,
    "templateId": 50,
}

_PENDING_BUFFER = {**_ACTIVE_BUFFER, "bufferStatus": "PENDING",
                   "leftInBuffer": -1, "totalCodes": -1,
                   "unavailableCodes": -1, "availableCodes": -1,
                   "totalPassed": -1}

_REJECTED_BUFFER = {**_PENDING_BUFFER, "bufferStatus": "REJECTED",
                    "rejectionReason": "Order declined: GTIN not found"}


class StubTransport:
    """Records the last request and returns a preset response."""

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


def _make_api(
    transport: StubTransport,
    signer: object | None = None,
) -> OrdersApi:
    return OrdersApi(
        transport=transport,
        oms_id=_OMS_ID,
        get_auth_headers=lambda: {"clientToken": "test-token"},
        signer=signer,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------

class TestCreate:
    def test_returns_response_model(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 5100},
        ))
        api = _make_api(transport)
        result = api.create(product_group="milk", products=[_PRODUCT])

        assert isinstance(result, CreateOrderResponse)
        assert result.oms_id == _OMS_ID
        assert result.order_id == _ORDER_ID
        assert result.expected_complete_timestamp == 5100

    def test_sends_post_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport)
        api.create(product_group="milk", products=[_PRODUCT])

        req = transport.last_request
        assert req is not None
        assert req.method == "POST"
        assert req.path == "/api/v3/order"

    def test_sends_oms_id_as_query_param(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport)
        api.create(product_group="milk", products=[_PRODUCT])

        assert transport.last_request is not None
        assert transport.last_request.params.get("omsId") == _OMS_ID

    def test_body_contains_product_group_and_products(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport)
        api.create(product_group="shoes", products=[_PRODUCT])

        req = transport.last_request
        assert req is not None and req.raw_body is not None
        body = json.loads(req.raw_body.decode())
        assert body["productGroup"] == "shoes"
        assert len(body["products"]) == 1
        p = body["products"][0]
        assert p["gtin"] == _GTIN
        assert p["quantity"] == 20
        assert p["serialNumberType"] == "OPERATOR"
        assert p["templateId"] == 50
        assert p["cisType"] == "UNIT"

    def test_omits_serial_numbers_when_not_provided(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport)
        api.create(product_group="milk", products=[_PRODUCT])

        req = transport.last_request
        assert req is not None and req.raw_body is not None
        body = json.loads(req.raw_body.decode())
        assert "serialNumbers" not in body["products"][0]

    def test_includes_serial_numbers_for_self_made(self) -> None:
        product = OrderProduct(
            gtin=_GTIN, quantity=2, serial_number_type="SELF_MADE",
            template_id=85, cis_type="UNIT",
            serial_numbers=["SN001", "SN002"],
        )
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport)
        api.create(product_group="furslp", products=[product])

        req = transport.last_request
        assert req is not None and req.raw_body is not None
        body = json.loads(req.raw_body.decode())
        assert body["products"][0]["serialNumbers"] == ["SN001", "SN002"]

    def test_includes_service_provider_id_when_given(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport)
        api.create(product_group="milk", products=[_PRODUCT],
                   service_provider_id="aaaa-bbbb")

        req = transport.last_request
        assert req is not None and req.raw_body is not None
        body = json.loads(req.raw_body.decode())
        assert body["serviceProviderId"] == "aaaa-bbbb"

    def test_omits_service_provider_id_when_not_given(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport)
        api.create(product_group="milk", products=[_PRODUCT])

        req = transport.last_request
        assert req is not None and req.raw_body is not None
        body = json.loads(req.raw_body.decode())
        assert "serviceProviderId" not in body

    def test_signs_body_with_signer(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport, signer=NoopSigner())
        api.create(product_group="milk", products=[_PRODUCT])

        req = transport.last_request
        assert req is not None
        assert "X-Signature" in req.headers

    def test_no_signature_without_signer(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport, signer=None)
        api.create(product_group="milk", products=[_PRODUCT])

        req = transport.last_request
        assert req is not None
        assert "X-Signature" not in req.headers

    def test_signer_receives_exact_body_bytes(self) -> None:
        from unittest.mock import MagicMock

        mock_signer = MagicMock()
        mock_signer.sign_bytes.return_value = "sig"

        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport, signer=mock_signer)
        api.create(product_group="milk", products=[_PRODUCT])

        req = transport.last_request
        assert req is not None and req.raw_body is not None
        mock_signer.sign_bytes.assert_called_once_with(req.raw_body)

    def test_sends_content_type_json(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport)
        api.create(product_group="milk", products=[_PRODUCT])

        req = transport.last_request
        assert req is not None
        assert req.headers.get("Content-Type") == "application/json"

    def test_sends_client_token_header(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        api = _make_api(transport)
        api.create(product_group="milk", products=[_PRODUCT])

        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == "test-token"


# ---------------------------------------------------------------------------
# get_status()
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_returns_list_of_buffer_info(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=[_ACTIVE_BUFFER],
        ))
        api = _make_api(transport)
        result = api.get_status(_ORDER_ID)

        assert len(result) == 1
        assert isinstance(result[0], BufferInfo)

    def test_parses_active_buffer_correctly(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=[_ACTIVE_BUFFER],
        ))
        api = _make_api(transport)
        buf = api.get_status(_ORDER_ID)[0]

        assert buf.buffer_status == "ACTIVE"
        assert buf.gtin == _GTIN
        assert buf.available_codes == 20
        assert buf.total_codes == 20
        assert buf.pools_exhausted is False
        assert buf.template_id == 50
        assert buf.oms_id == _OMS_ID
        assert buf.order_id == _ORDER_ID

    def test_parses_pending_buffer_correctly(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=[_PENDING_BUFFER],
        ))
        api = _make_api(transport)
        buf = api.get_status(_ORDER_ID)[0]

        assert buf.buffer_status == "PENDING"
        assert buf.rejection_reason is None

    def test_parses_rejected_buffer_correctly(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=[_REJECTED_BUFFER],
        ))
        api = _make_api(transport)
        buf = api.get_status(_ORDER_ID)[0]

        assert buf.buffer_status == "REJECTED"
        assert buf.rejection_reason is not None
        assert "GTIN not found" in buf.rejection_reason

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=[_ACTIVE_BUFFER],
        ))
        api = _make_api(transport)
        api.get_status(_ORDER_ID)

        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/order/status"

    def test_sends_order_id_and_oms_id_as_params(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=[_ACTIVE_BUFFER],
        ))
        api = _make_api(transport)
        api.get_status(_ORDER_ID)

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("orderId") == _ORDER_ID

    def test_includes_gtin_param_when_provided(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=[_ACTIVE_BUFFER],
        ))
        api = _make_api(transport)
        api.get_status(_ORDER_ID, gtin=_GTIN)

        req = transport.last_request
        assert req is not None
        assert req.params.get("gtin") == _GTIN

    def test_omits_gtin_param_when_not_provided(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=[_ACTIVE_BUFFER],
        ))
        api = _make_api(transport)
        api.get_status(_ORDER_ID)

        req = transport.last_request
        assert req is not None
        assert "gtin" not in req.params

    def test_returns_multiple_buffers(self) -> None:
        buf2 = {**_ACTIVE_BUFFER, "gtin": "09876543210987"}
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=[_ACTIVE_BUFFER, buf2],
        ))
        api = _make_api(transport)
        result = api.get_status(_ORDER_ID)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# get_codes()
# ---------------------------------------------------------------------------

class TestGetCodes:
    _CODES_RESP = {
        "omsId": _OMS_ID,
        "codes": ["0104601653003004621=rxDV3M\\u001d93VXQI"],
        "blockId": _BLOCK_ID,
    }

    def test_returns_response_model(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CODES_RESP,
        ))
        api = _make_api(transport)
        result = api.get_codes(_ORDER_ID, _GTIN, quantity=1)

        assert isinstance(result, GetCodesResponse)
        assert result.oms_id == _OMS_ID
        assert result.block_id == _BLOCK_ID
        assert len(result.codes) == 1

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CODES_RESP,
        ))
        api = _make_api(transport)
        api.get_codes(_ORDER_ID, _GTIN, quantity=15)

        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/codes"

    def test_sends_correct_query_params(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CODES_RESP,
        ))
        api = _make_api(transport)
        api.get_codes(_ORDER_ID, _GTIN, quantity=15)

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("orderId") == _ORDER_ID
        assert req.params.get("gtin") == _GTIN
        assert req.params.get("quantity") == "15"

    def test_codes_are_returned_as_list(self) -> None:
        resp_body = {**self._CODES_RESP, "codes": ["code1", "code2", "code3"]}
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=resp_body,
        ))
        api = _make_api(transport)
        result = api.get_codes(_ORDER_ID, _GTIN, quantity=3)

        assert result.codes == ["code1", "code2", "code3"]


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------

class TestClose:
    _CLOSE_RESP = {"omsId": _OMS_ID}

    def test_returns_response_model(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CLOSE_RESP,
        ))
        api = _make_api(transport)
        result = api.close(_ORDER_ID)

        assert isinstance(result, CloseOrderResponse)
        assert result.oms_id == _OMS_ID

    def test_sends_post_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CLOSE_RESP,
        ))
        api = _make_api(transport)
        api.close(_ORDER_ID)

        req = transport.last_request
        assert req is not None
        assert req.method == "POST"
        assert req.path == "/api/v3/order/close"

    def test_sends_oms_id_as_query_param(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CLOSE_RESP,
        ))
        api = _make_api(transport)
        api.close(_ORDER_ID)

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    def test_body_contains_order_id(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CLOSE_RESP,
        ))
        api = _make_api(transport)
        api.close(_ORDER_ID)

        req = transport.last_request
        assert req is not None and req.raw_body is not None
        body = json.loads(req.raw_body.decode())
        assert body["orderId"] == _ORDER_ID

    def test_body_includes_gtin_when_provided(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CLOSE_RESP,
        ))
        api = _make_api(transport)
        api.close(_ORDER_ID, gtin=_GTIN)

        req = transport.last_request
        assert req is not None and req.raw_body is not None
        body = json.loads(req.raw_body.decode())
        assert body["gtin"] == _GTIN

    def test_body_omits_gtin_when_not_provided(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CLOSE_RESP,
        ))
        api = _make_api(transport)
        api.close(_ORDER_ID)

        req = transport.last_request
        assert req is not None and req.raw_body is not None
        body = json.loads(req.raw_body.decode())
        assert "gtin" not in body

    def test_signs_body_with_signer(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CLOSE_RESP,
        ))
        api = _make_api(transport, signer=NoopSigner())
        api.close(_ORDER_ID)

        req = transport.last_request
        assert req is not None
        assert "X-Signature" in req.headers

    def test_no_signature_without_signer(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=self._CLOSE_RESP,
        ))
        api = _make_api(transport, signer=None)
        api.close(_ORDER_ID)

        req = transport.last_request
        assert req is not None
        assert "X-Signature" not in req.headers


# ---------------------------------------------------------------------------
# SuzClient wiring smoke-test
# ---------------------------------------------------------------------------

class TestSuzClientOrdersWiring:
    def test_client_orders_is_available(self) -> None:
        from suz_sdk.client import SuzClient

        client = SuzClient(oms_id=_OMS_ID)
        assert isinstance(client.orders, OrdersApi)

    def test_client_orders_uses_main_transport(self) -> None:
        from suz_sdk.client import SuzClient

        stub = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsId": _OMS_ID, "orderId": _ORDER_ID, "expectedCompleteTimestamp": 100},
        ))
        client = SuzClient(oms_id=_OMS_ID, transport=stub)
        result = client.orders.create(product_group="milk", products=[_PRODUCT])

        assert result.order_id == _ORDER_ID
        assert stub.last_request is not None
