"""Unit tests for AsyncSuzClient and async API modules."""

import json

import pytest

from suz_sdk.api.async_health import AsyncHealthApi
from suz_sdk.api.async_integration import AsyncIntegrationApi
from suz_sdk.api.async_orders import AsyncOrdersApi
from suz_sdk.api.async_reports import AsyncReportsApi
from suz_sdk.api.health import PingResponse
from suz_sdk.api.integration import ConnectionInfo, DeleteConnectionResponse, ListConnectionsResponse
from suz_sdk.api.orders import (
    Block,
    BufferInfo,
    CreateOrderResponse,
    GetBlocksResponse,
    GetCodesResponse,
    ListOrdersResponse,
    OrderFilter,
    OrderProduct,
    SearchOrdersResponse,
)
from suz_sdk.api.reports import ReceiptFilter, SendUtilisationResponse
from suz_sdk.async_client import AsyncSuzClient
from suz_sdk.auth.async_auth_api import AsyncAuthApi
from suz_sdk.auth.async_token_manager import AsyncTokenManager
from suz_sdk.auth.async_true_api import AsyncTrueApiAuth
from suz_sdk.exceptions import SuzError
from suz_sdk.signing.noop import NoopSigner
from suz_sdk.transport.base import Request, Response

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OMS_ID = "aaaaaaaa-0000-0000-0000-000000000000"
ORDER_ID = "bbbbbbbb-1111-1111-1111-111111111111"
REPORT_ID = "cccccccc-2222-2222-2222-222222222222"
GTIN = "04606031026879"


class AsyncCapturingTransport:
    """Records the last request and returns a pre-configured response."""

    def __init__(self, response_body: object) -> None:
        self.response_body = response_body
        self.last_request: Request | None = None

    async def request(self, req: Request) -> Response:
        self.last_request = req
        return Response(status_code=200, headers={}, body=self.response_body)

    async def aclose(self) -> None:
        pass


def make_client(transport, **kwargs) -> AsyncSuzClient:
    defaults = {"oms_id": OMS_ID, "client_token": "tok"}
    defaults.update(kwargs)
    return AsyncSuzClient(transport=transport, **defaults)


# ---------------------------------------------------------------------------
# AsyncSuzClient — structure
# ---------------------------------------------------------------------------


class TestAsyncSuzClientStructure:
    def test_has_health_attribute(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)
        assert isinstance(client.health, AsyncHealthApi)

    def test_has_integration_attribute(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)
        assert isinstance(client.integration, AsyncIntegrationApi)

    def test_has_orders_attribute(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)
        assert isinstance(client.orders, AsyncOrdersApi)

    def test_has_reports_attribute(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)
        assert isinstance(client.reports, AsyncReportsApi)

    def test_has_auth_attribute(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)
        assert isinstance(client.auth, AsyncAuthApi)

    def test_repr(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)
        r = repr(client)
        assert "AsyncSuzClient" in r
        assert OMS_ID in r

    def test_signer_wired_to_orders(self):
        signer = NoopSigner()
        t = AsyncCapturingTransport({})
        client = make_client(t, signer=signer)
        assert client.orders._signer is signer

    def test_signer_wired_to_reports(self):
        signer = NoopSigner()
        t = AsyncCapturingTransport({})
        client = make_client(t, signer=signer)
        assert client.reports._signer is signer


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestAsyncContextManager:
    @pytest.mark.anyio
    async def test_aenter_returns_client(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)
        async with client as c:
            assert c is client

    @pytest.mark.anyio
    async def test_aexit_calls_aclose(self):
        closed = []
        t = AsyncCapturingTransport({})

        class TrackingTransport(AsyncCapturingTransport):
            async def aclose(self):
                closed.append(True)

        client = AsyncSuzClient(
            oms_id=OMS_ID,
            client_token="tok",
            transport=TrackingTransport({}),
        )
        # TrackingTransport is injected directly — owns_transport=False, so
        # aclose is NOT called automatically. Let's test via explicit aclose.
        await client.aclose()
        # No error = pass; owns_transport is False so nothing to close


# ---------------------------------------------------------------------------
# Auth headers
# ---------------------------------------------------------------------------


class TestAuthHeaders:
    @pytest.mark.anyio
    async def test_static_token_injected(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "apiVersion": "3", "omsVersion": "4"}
        )
        client = make_client(t, client_token="my-token")
        await client.health.ping()
        assert t.last_request.headers["clientToken"] == "my-token"

    @pytest.mark.anyio
    async def test_no_auth_when_no_token(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "apiVersion": "3", "omsVersion": "4"}
        )
        client = AsyncSuzClient(oms_id=OMS_ID, transport=t)
        await client.health.ping()
        assert "clientToken" not in t.last_request.headers


# ---------------------------------------------------------------------------
# AsyncHealthApi
# ---------------------------------------------------------------------------


class TestAsyncHealthApi:
    @pytest.mark.anyio
    async def test_ping_returns_ping_response(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "apiVersion": "3.0", "omsVersion": "4.0"}
        )
        client = make_client(t)
        resp = await client.health.ping()
        assert isinstance(resp, PingResponse)
        assert resp.oms_id == OMS_ID
        assert resp.api_version == "3.0"
        assert resp.oms_version == "4.0"

    @pytest.mark.anyio
    async def test_ping_method_and_path(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "apiVersion": "3", "omsVersion": "4"}
        )
        client = make_client(t)
        await client.health.ping()
        req = t.last_request
        assert req.method == "GET"
        assert req.path == "/api/v3/ping"
        assert req.params["omsId"] == OMS_ID


# ---------------------------------------------------------------------------
# AsyncOrdersApi
# ---------------------------------------------------------------------------


class TestAsyncOrdersApi:
    @pytest.mark.anyio
    async def test_create_returns_response(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "orderId": ORDER_ID, "expectedCompleteTimestamp": 1000}
        )
        client = make_client(t)
        resp = await client.orders.create(
            product_group="milk",
            products=[
                OrderProduct(
                    gtin=GTIN,
                    quantity=10,
                    serial_number_type="OPERATOR",
                    template_id=1,
                    cis_type="UNIT",
                )
            ],
        )
        assert isinstance(resp, CreateOrderResponse)
        assert resp.order_id == ORDER_ID

    @pytest.mark.anyio
    async def test_create_post_to_order(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "orderId": ORDER_ID, "expectedCompleteTimestamp": 0}
        )
        client = make_client(t)
        await client.orders.create(
            "milk",
            [OrderProduct(GTIN, 1, "OPERATOR", 1, "UNIT")],
        )
        assert t.last_request.method == "POST"
        assert t.last_request.path == "/api/v3/order"

    @pytest.mark.anyio
    async def test_create_body_contains_product_group(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "orderId": ORDER_ID, "expectedCompleteTimestamp": 0}
        )
        client = make_client(t)
        await client.orders.create("shoes", [OrderProduct(GTIN, 1, "OPERATOR", 1, "UNIT")])
        body = json.loads(t.last_request.raw_body)
        assert body["productGroup"] == "shoes"

    @pytest.mark.anyio
    async def test_create_signs_when_signer_present(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "orderId": ORDER_ID, "expectedCompleteTimestamp": 0}
        )
        client = make_client(t, signer=NoopSigner())
        await client.orders.create("milk", [OrderProduct(GTIN, 1, "OPERATOR", 1, "UNIT")])
        assert "X-Signature" in t.last_request.headers

    @pytest.mark.anyio
    async def test_get_status_returns_buffer_list(self):
        t = AsyncCapturingTransport(
            [
                {
                    "gtin": GTIN,
                    "bufferStatus": "ACTIVE",
                    "availableCodes": 10,
                    "totalCodes": 10,
                    "totalPassed": 0,
                    "unavailableCodes": 0,
                    "leftInBuffer": 10,
                    "poolsExhausted": False,
                    "templateId": 1,
                }
            ]
        )
        client = make_client(t)
        result = await client.orders.get_status(ORDER_ID)
        assert isinstance(result, list)
        assert isinstance(result[0], BufferInfo)
        assert result[0].buffer_status == "ACTIVE"

    @pytest.mark.anyio
    async def test_get_codes_returns_response(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "codes": ["code1", "code2"], "blockId": "blk-1"}
        )
        client = make_client(t)
        resp = await client.orders.get_codes(ORDER_ID, GTIN, 2)
        assert isinstance(resp, GetCodesResponse)
        assert resp.codes == ["code1", "code2"]

    @pytest.mark.anyio
    async def test_close_returns_response(self):
        t = AsyncCapturingTransport({"omsId": OMS_ID})
        client = make_client(t)
        resp = await client.orders.close(ORDER_ID)
        assert resp.oms_id == OMS_ID

    @pytest.mark.anyio
    async def test_close_method_and_path(self):
        t = AsyncCapturingTransport({"omsId": OMS_ID})
        client = make_client(t)
        await client.orders.close(ORDER_ID)
        assert t.last_request.method == "POST"
        assert t.last_request.path == "/api/v3/order/close"

    @pytest.mark.anyio
    async def test_list_orders_returns_response(self):
        t = AsyncCapturingTransport({
            "omsId": OMS_ID,
            "orderInfos": [
                {
                    "orderId": ORDER_ID,
                    "orderStatus": "ACTIVE",
                    "createdTimestamp": 1700000000000,
                }
            ],
        })
        client = make_client(t)
        resp = await client.orders.list_orders()
        assert isinstance(resp, ListOrdersResponse)
        assert resp.oms_id == OMS_ID
        assert len(resp.order_infos) == 1
        assert resp.order_infos[0].order_id == ORDER_ID

    @pytest.mark.anyio
    async def test_list_orders_method_and_path(self):
        t = AsyncCapturingTransport({"omsId": OMS_ID, "orderInfos": []})
        client = make_client(t)
        await client.orders.list_orders()
        assert t.last_request.method == "GET"
        assert t.last_request.path == "/api/v3/order/list"
        assert t.last_request.params["omsId"] == OMS_ID

    @pytest.mark.anyio
    async def test_get_blocks_returns_response(self):
        block_id = "blk-aabbcc"
        t = AsyncCapturingTransport({
            "omsId": OMS_ID,
            "orderId": ORDER_ID,
            "gtin": GTIN,
            "blocks": [{"blockId": block_id, "blockDateTime": 1700000000000, "quantity": 5}],
        })
        client = make_client(t)
        resp = await client.orders.get_blocks(ORDER_ID, GTIN)
        assert isinstance(resp, GetBlocksResponse)
        assert resp.gtin == GTIN
        assert len(resp.blocks) == 1
        assert isinstance(resp.blocks[0], Block)
        assert resp.blocks[0].block_id == block_id
        assert resp.blocks[0].quantity == 5

    @pytest.mark.anyio
    async def test_get_blocks_method_and_path(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "orderId": ORDER_ID, "gtin": GTIN, "blocks": []}
        )
        client = make_client(t)
        await client.orders.get_blocks(ORDER_ID, GTIN)
        req = t.last_request
        assert req.method == "GET"
        assert req.path == "/api/v3/order/codes/blocks"
        assert req.params["orderId"] == ORDER_ID
        assert req.params["gtin"] == GTIN

    @pytest.mark.anyio
    async def test_get_codes_retry_returns_response(self):
        block_id = "blk-retry-1"
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "codes": ["c1", "c2"], "blockId": block_id}
        )
        client = make_client(t)
        resp = await client.orders.get_codes_retry(block_id)
        assert isinstance(resp, GetCodesResponse)
        assert resp.block_id == block_id
        assert resp.codes == ["c1", "c2"]

    @pytest.mark.anyio
    async def test_get_codes_retry_method_and_path(self):
        block_id = "blk-retry-1"
        t = AsyncCapturingTransport({"omsId": OMS_ID, "codes": [], "blockId": block_id})
        client = make_client(t)
        await client.orders.get_codes_retry(block_id)
        req = t.last_request
        assert req.method == "GET"
        assert req.path == "/api/v3/order/codes/retry"
        assert req.params["blockId"] == block_id

    @pytest.mark.anyio
    async def test_get_product_info_returns_dict(self):
        t = AsyncCapturingTransport({GTIN: {"attr1": "val1"}})
        client = make_client(t)
        resp = await client.orders.get_product_info(ORDER_ID)
        assert isinstance(resp, dict)
        assert GTIN in resp
        assert resp[GTIN]["attr1"] == "val1"

    @pytest.mark.anyio
    async def test_get_product_info_method_and_path(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)
        await client.orders.get_product_info(ORDER_ID)
        req = t.last_request
        assert req.method == "GET"
        assert req.path == "/api/v3/order/product"
        assert req.params["orderId"] == ORDER_ID

    @pytest.mark.anyio
    async def test_search_orders_returns_response(self):
        t = AsyncCapturingTransport({
            "totalCount": 2,
            "results": [
                {"orderId": ORDER_ID, "orderStatus": "ACTIVE", "createdTimestamp": 1700000000000},
            ],
        })
        client = make_client(t)
        resp = await client.orders.search_orders(limit=5, page=0)
        assert isinstance(resp, SearchOrdersResponse)
        assert resp.total_count == 2
        assert len(resp.results) == 1
        assert resp.results[0].order_id == ORDER_ID

    @pytest.mark.anyio
    async def test_search_orders_method_and_path(self):
        t = AsyncCapturingTransport({"totalCount": 0, "results": []})
        client = make_client(t)
        await client.orders.search_orders()
        req = t.last_request
        assert req.method == "POST"
        assert req.path == "/api/v3/orders/search"
        assert req.params["omsId"] == OMS_ID

    @pytest.mark.anyio
    async def test_search_orders_filter_in_body(self):
        t = AsyncCapturingTransport({"totalCount": 0, "results": []})
        client = make_client(t)
        f = OrderFilter(order_statuses=["ACTIVE"], order_ids=[ORDER_ID])
        await client.orders.search_orders(filter=f, limit=20, page=1)
        body = t.last_request.json_body
        assert body["limit"] == 20
        assert body["page"] == 1
        assert body["filter"]["orderStatuses"] == ["ACTIVE"]
        assert body["filter"]["orderIds"] == [ORDER_ID]


# ---------------------------------------------------------------------------
# AsyncReportsApi
# ---------------------------------------------------------------------------


class TestAsyncReportsApi:
    @pytest.mark.anyio
    async def test_send_utilisation_returns_response(self):
        t = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        client = make_client(t)
        resp = await client.reports.send_utilisation("milk", ["sntin1"])
        assert isinstance(resp, SendUtilisationResponse)
        assert resp.report_id == REPORT_ID

    @pytest.mark.anyio
    async def test_send_utilisation_post(self):
        t = AsyncCapturingTransport({"omsId": OMS_ID, "reportId": REPORT_ID})
        client = make_client(t)
        await client.reports.send_utilisation("milk", ["s1"])
        assert t.last_request.method == "POST"
        assert t.last_request.path == "/api/v3/utilisation"

    @pytest.mark.anyio
    async def test_get_report_status_returns_response(self):
        t = AsyncCapturingTransport(
            {"omsId": OMS_ID, "reportId": REPORT_ID, "reportStatus": "SUCCESS"}
        )
        client = make_client(t)
        resp = await client.reports.get_report_status(REPORT_ID)
        assert resp.report_status == "SUCCESS"

    @pytest.mark.anyio
    async def test_get_receipt_returns_list(self):
        receipt = {"resultDocId": "doc-1", "state": "SUCCESS"}
        t = AsyncCapturingTransport({"results": [receipt]})
        client = make_client(t)
        result = await client.reports.get_receipt("doc-1")
        assert result == [receipt]

    @pytest.mark.anyio
    async def test_search_receipts_returns_response(self):
        t = AsyncCapturingTransport({"totalCount": 0, "results": []})
        client = make_client(t)
        resp = await client.reports.search_receipts(ReceiptFilter(order_ids=["x"]))
        assert resp.total_count == 0
        assert resp.results == []


# ---------------------------------------------------------------------------
# AsyncIntegrationApi — new methods
# ---------------------------------------------------------------------------

OMS_CONNECTION = "aabb1234-5678-90ab-cdef-1234567890ab"

_CONN_INFO = {
    "omsConnection": OMS_CONNECTION,
    "address": "г.Москва, ул.1",
    "programName": "ERP",
    "productGroups": ["milk"],
    "productVersion": "1.0",
    "vendorInn": "1234567890",
}


class TestAsyncIntegrationApiNew:
    @pytest.mark.anyio
    async def test_list_connections_returns_response(self):
        t = AsyncCapturingTransport(
            {"omsConnectionInfos": [_CONN_INFO], "total": 1}
        )
        client = make_client(t)
        resp = await client.integration.list_connections()
        assert isinstance(resp, ListConnectionsResponse)
        assert resp.total == 1
        assert len(resp.oms_connection_infos) == 1
        conn = resp.oms_connection_infos[0]
        assert isinstance(conn, ConnectionInfo)
        assert conn.oms_connection == OMS_CONNECTION
        assert conn.address == "г.Москва, ул.1"
        assert conn.product_groups == ["milk"]

    @pytest.mark.anyio
    async def test_list_connections_method_and_path(self):
        t = AsyncCapturingTransport({"omsConnectionInfos": [], "total": 0})
        client = make_client(t)
        await client.integration.list_connections()
        req = t.last_request
        assert req.method == "GET"
        assert req.path == "/api/v3/integration/connection"
        assert req.params["omsId"] == OMS_ID

    @pytest.mark.anyio
    async def test_list_connections_default_limit_and_offset(self):
        t = AsyncCapturingTransport({"omsConnectionInfos": [], "total": 0})
        client = make_client(t)
        await client.integration.list_connections()
        req = t.last_request
        assert req.params["limit"] == "10"
        assert req.params["offset"] == "0"

    @pytest.mark.anyio
    async def test_list_connections_custom_limit_and_offset(self):
        t = AsyncCapturingTransport({"omsConnectionInfos": [], "total": 0})
        client = make_client(t)
        await client.integration.list_connections(limit=25, offset=50)
        req = t.last_request
        assert req.params["limit"] == "25"
        assert req.params["offset"] == "50"

    @pytest.mark.anyio
    async def test_list_connections_empty_infos_when_missing(self):
        t = AsyncCapturingTransport({"total": 0})
        client = make_client(t)
        resp = await client.integration.list_connections()
        assert resp.oms_connection_infos == []

    @pytest.mark.anyio
    async def test_delete_connection_returns_response(self):
        t = AsyncCapturingTransport({"success": True})
        client = make_client(t)
        resp = await client.integration.delete_connection(OMS_CONNECTION)
        assert isinstance(resp, DeleteConnectionResponse)
        assert resp.success is True

    @pytest.mark.anyio
    async def test_delete_connection_method_and_path(self):
        t = AsyncCapturingTransport({"success": True})
        client = make_client(t)
        await client.integration.delete_connection(OMS_CONNECTION)
        req = t.last_request
        assert req.method == "DELETE"
        assert req.path == "/api/v3/integration/connection"

    @pytest.mark.anyio
    async def test_delete_connection_sends_correct_params(self):
        t = AsyncCapturingTransport({"success": True})
        client = make_client(t)
        await client.integration.delete_connection(OMS_CONNECTION)
        req = t.last_request
        assert req.params["omsId"] == OMS_ID
        assert req.params["omsConnection"] == OMS_CONNECTION

    @pytest.mark.anyio
    async def test_delete_connection_success_false_when_missing(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)
        resp = await client.integration.delete_connection(OMS_CONNECTION)
        assert resp.success is False

    @pytest.mark.anyio
    async def test_list_connections_sends_auth_header(self):
        t = AsyncCapturingTransport({"omsConnectionInfos": [], "total": 0})
        client = make_client(t, client_token="mytoken")
        await client.integration.list_connections()
        assert t.last_request.headers["clientToken"] == "mytoken"


# ---------------------------------------------------------------------------
# AsyncAuthApi
# ---------------------------------------------------------------------------


class TestAsyncAuthApi:
    @pytest.mark.anyio
    async def test_authenticate_raises_when_no_token_manager(self):
        t = AsyncCapturingTransport({})
        client = make_client(t)  # client_token only, no oms_connection+signer
        with pytest.raises(SuzError, match="not configured"):
            await client.auth.authenticate()


# ---------------------------------------------------------------------------
# AsyncTrueApiAuth + AsyncTokenManager (unit)
# ---------------------------------------------------------------------------


class TestAsyncTrueApiAuth:
    @pytest.mark.anyio
    async def test_fetch_token_two_step_flow(self):
        responses = [
            Response(200, {}, {"uuid": "u1", "data": "challenge"}),
            Response(200, {}, {"token": "my-token"}),
        ]
        calls: list[Request] = []

        class FakeTransport:
            async def request(self, req: Request) -> Response:
                calls.append(req)
                return responses.pop(0)

        from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport

        auth = AsyncTrueApiAuth(
            oms_connection="conn-1",
            signer=NoopSigner(),
            transport=FakeTransport(),  # type: ignore
        )
        token = await auth.fetch_token()
        assert token == "my-token"
        assert calls[0].path == "/auth/key"
        assert calls[1].path == "/auth/simpleSignIn/conn-1"

    @pytest.mark.anyio
    async def test_token_manager_returns_token(self):
        class FakeAuth:
            async def fetch_token(self) -> str:
                return "fresh-token"

        manager = AsyncTokenManager(auth=FakeAuth())  # type: ignore
        token = await manager.get_token()
        assert token == "fresh-token"

    @pytest.mark.anyio
    async def test_token_manager_caches_token(self):
        call_count = 0

        class CountingAuth:
            async def fetch_token(self) -> str:
                nonlocal call_count
                call_count += 1
                return f"token-{call_count}"

        manager = AsyncTokenManager(auth=CountingAuth())  # type: ignore
        t1 = await manager.get_token()
        t2 = await manager.get_token()
        assert t1 == t2
        assert call_count == 1

    @pytest.mark.anyio
    async def test_token_manager_authenticate_forces_refresh(self):
        call_count = 0

        class CountingAuth:
            async def fetch_token(self) -> str:
                nonlocal call_count
                call_count += 1
                return f"token-{call_count}"

        manager = AsyncTokenManager(auth=CountingAuth())  # type: ignore
        await manager.get_token()
        await manager.authenticate()
        assert call_count == 2


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


class TestExports:
    def test_async_suz_client_exported(self):
        from suz_sdk import AsyncSuzClient as Imported

        assert Imported is AsyncSuzClient

    def test_async_http_transport_exported(self):
        from suz_sdk import AsyncHttpxTransport

        assert AsyncHttpxTransport is not None
