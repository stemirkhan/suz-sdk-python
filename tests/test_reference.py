"""Tests for ReferenceApi and AsyncReferenceApi.

Covers:
  - HTTP method and path correctness
  - Query parameter injection (omsId, orderId, gtin, limit, skip)
  - Response model field mapping
  - Auth header injection
  - SuzClient / AsyncSuzClient wiring
"""

import pytest

from suz_sdk.api.reference import (
    AsyncReferenceApi,
    ModResponse,
    ProvidersResponse,
    QualityCisListResponse,
    QualityResponse,
    ReferenceApi,
)
from suz_sdk.transport.base import Request, Response

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_OMS_ID = "cdf12109-10d3-11e6-8b6f-0050569977a1"
_ORDER_ID = "b024ae09-ef7c-449e-b461-05d8eb116c79"
_GTIN = "04606031026879"
_TOKEN = "test-client-token"

# ---------------------------------------------------------------------------
# Sync stub transport
# ---------------------------------------------------------------------------


class StubTransport:
    """Records the last request and returns a preset Response or raises."""

    def __init__(
        self,
        response: Response | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._response = response
        self._exc = exc
        self.last_request: Request | None = None

    def request(self, req: Request) -> Response:
        self.last_request = req
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


# ---------------------------------------------------------------------------
# Async stub transport
# ---------------------------------------------------------------------------


class AsyncStubTransport:
    """Async version of StubTransport."""

    def __init__(
        self,
        response: Response | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._response = response
        self._exc = exc
        self.last_request: Request | None = None

    async def request(self, req: Request) -> Response:
        self.last_request = req
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response

    async def aclose(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_api(transport: StubTransport, token: str | None = _TOKEN) -> ReferenceApi:
    def get_auth_headers() -> dict[str, str]:
        return {"clientToken": token} if token else {}

    return ReferenceApi(
        transport=transport,
        oms_id=_OMS_ID,
        get_auth_headers=get_auth_headers,
    )


def _make_async_api(
    transport: AsyncStubTransport, token: str | None = _TOKEN
) -> AsyncReferenceApi:
    async def get_auth_headers() -> dict[str, str]:
        return {"clientToken": token} if token else {}

    return AsyncReferenceApi(
        transport=transport,
        oms_id=_OMS_ID,
        get_auth_headers=get_auth_headers,
    )


def _ok(body: object) -> Response:
    return Response(status_code=200, headers={}, body=body)


# ---------------------------------------------------------------------------
# get_providers — sync
# ---------------------------------------------------------------------------


class TestGetProviders:
    def test_returns_providers_response(self) -> None:
        providers_data = [{"id": "prov1", "name": "Provider One"}]
        transport = StubTransport(response=_ok({"providers": providers_data}))
        api = _make_api(transport)
        result = api.get_providers()
        assert isinstance(result, ProvidersResponse)
        assert result.providers == providers_data

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=_ok({"providers": []}))
        api = _make_api(transport)
        api.get_providers()
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/providers"

    def test_sends_oms_id_query_param(self) -> None:
        transport = StubTransport(response=_ok({"providers": []}))
        api = _make_api(transport)
        api.get_providers()
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=_ok({"providers": []}))
        api = _make_api(transport, token=_TOKEN)
        api.get_providers()
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_no_token_sends_no_auth_header(self) -> None:
        transport = StubTransport(response=_ok({"providers": []}))
        api = _make_api(transport, token=None)
        api.get_providers()
        req = transport.last_request
        assert req is not None
        assert "clientToken" not in req.headers

    def test_empty_providers_list(self) -> None:
        transport = StubTransport(response=_ok({"providers": []}))
        api = _make_api(transport)
        result = api.get_providers()
        assert result.providers == []

    def test_sends_accept_json_header(self) -> None:
        transport = StubTransport(response=_ok({"providers": []}))
        api = _make_api(transport)
        api.get_providers()
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Accept") == "application/json"


# ---------------------------------------------------------------------------
# get_quality — sync
# ---------------------------------------------------------------------------


class TestGetQuality:
    def test_returns_quality_response(self) -> None:
        transport = StubTransport(
            response=_ok({"orderId": _ORDER_ID, "bufferStatus": "ACTIVE"})
        )
        api = _make_api(transport)
        result = api.get_quality(_ORDER_ID)
        assert isinstance(result, QualityResponse)
        assert result.order_id == _ORDER_ID
        assert result.buffer_status == "ACTIVE"

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(
            response=_ok({"orderId": _ORDER_ID, "bufferStatus": "ACTIVE"})
        )
        api = _make_api(transport)
        api.get_quality(_ORDER_ID)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/quality"

    def test_sends_oms_id_and_order_id(self) -> None:
        transport = StubTransport(
            response=_ok({"orderId": _ORDER_ID, "bufferStatus": "PENDING"})
        )
        api = _make_api(transport)
        api.get_quality(_ORDER_ID)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("orderId") == _ORDER_ID

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(
            response=_ok({"orderId": _ORDER_ID, "bufferStatus": "ACTIVE"})
        )
        api = _make_api(transport, token=_TOKEN)
        api.get_quality(_ORDER_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_extra_fields_preserved(self) -> None:
        transport = StubTransport(
            response=_ok(
                {
                    "orderId": _ORDER_ID,
                    "bufferStatus": "ACTIVE",
                    "someExtraField": "extra_value",
                }
            )
        )
        api = _make_api(transport)
        result = api.get_quality(_ORDER_ID)
        assert result.model_extra is not None
        assert result.model_extra.get("someExtraField") == "extra_value"

    def test_rejected_buffer_status(self) -> None:
        transport = StubTransport(
            response=_ok({"orderId": _ORDER_ID, "bufferStatus": "REJECTED"})
        )
        api = _make_api(transport)
        result = api.get_quality(_ORDER_ID)
        assert result.buffer_status == "REJECTED"


# ---------------------------------------------------------------------------
# get_quality_cis_list — sync
# ---------------------------------------------------------------------------


class TestGetQualityCisList:
    def test_returns_quality_cis_list_response(self) -> None:
        cis_items = [{"cis": "010123456789012321abc"}, {"cis": "010123456789012321def"}]
        transport = StubTransport(
            response=_ok({"totalCount": 2, "results": cis_items})
        )
        api = _make_api(transport)
        result = api.get_quality_cis_list(_ORDER_ID, _GTIN)
        assert isinstance(result, QualityCisListResponse)
        assert result.total_count == 2
        assert result.results == cis_items

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_api(transport)
        api.get_quality_cis_list(_ORDER_ID, _GTIN)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/quality/cisList"

    def test_sends_required_query_params(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_api(transport)
        api.get_quality_cis_list(_ORDER_ID, _GTIN)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("orderId") == _ORDER_ID
        assert req.params.get("gtin") == _GTIN

    def test_sends_optional_limit_and_skip(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_api(transport)
        api.get_quality_cis_list(_ORDER_ID, _GTIN, limit=10, skip=20)
        req = transport.last_request
        assert req is not None
        assert req.params.get("limit") == "10"
        assert req.params.get("skip") == "20"

    def test_omits_limit_and_skip_when_none(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_api(transport)
        api.get_quality_cis_list(_ORDER_ID, _GTIN)
        req = transport.last_request
        assert req is not None
        assert "limit" not in req.params
        assert "skip" not in req.params

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_api(transport, token=_TOKEN)
        api.get_quality_cis_list(_ORDER_ID, _GTIN)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_empty_results(self) -> None:
        transport = StubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_api(transport)
        result = api.get_quality_cis_list(_ORDER_ID, _GTIN)
        assert result.total_count == 0
        assert result.results == []


# ---------------------------------------------------------------------------
# get_mod — sync
# ---------------------------------------------------------------------------


class TestGetMod:
    def test_returns_mod_response(self) -> None:
        transport = StubTransport(response=_ok({"mod": "SUZ_OMS_v3"}))
        api = _make_api(transport)
        result = api.get_mod()
        assert isinstance(result, ModResponse)
        assert result.mod == "SUZ_OMS_v3"

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=_ok({"mod": "SUZ_OMS_v3"}))
        api = _make_api(transport)
        api.get_mod()
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/mod"

    def test_sends_oms_id_query_param(self) -> None:
        transport = StubTransport(response=_ok({"mod": "SUZ_OMS_v3"}))
        api = _make_api(transport)
        api.get_mod()
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=_ok({"mod": "SUZ_OMS_v3"}))
        api = _make_api(transport, token=_TOKEN)
        api.get_mod()
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_sends_accept_json_header(self) -> None:
        transport = StubTransport(response=_ok({"mod": "SUZ_OMS_v3"}))
        api = _make_api(transport)
        api.get_mod()
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Accept") == "application/json"


# ---------------------------------------------------------------------------
# SuzClient wiring — sync
# ---------------------------------------------------------------------------


class TestSuzClientWiring:
    def test_client_has_reference_attribute(self) -> None:
        from suz_sdk.client import SuzClient

        transport = StubTransport(response=_ok({}))
        client = SuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        assert isinstance(client.reference, ReferenceApi)

    def test_client_reference_get_providers(self) -> None:
        from suz_sdk.client import SuzClient

        transport = StubTransport(response=_ok({"providers": [{"id": "p1"}]}))
        client = SuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        result = client.reference.get_providers()
        assert result.providers == [{"id": "p1"}]
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_client_reference_get_mod(self) -> None:
        from suz_sdk.client import SuzClient

        transport = StubTransport(response=_ok({"mod": "modX"}))
        client = SuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        result = client.reference.get_mod()
        assert result.mod == "modX"


# ---------------------------------------------------------------------------
# Async get_providers
# ---------------------------------------------------------------------------


class TestAsyncGetProviders:
    @pytest.mark.anyio
    async def test_returns_providers_response(self) -> None:
        providers_data = [{"id": "prov1"}]
        transport = AsyncStubTransport(response=_ok({"providers": providers_data}))
        api = _make_async_api(transport)
        result = await api.get_providers()
        assert isinstance(result, ProvidersResponse)
        assert result.providers == providers_data

    @pytest.mark.anyio
    async def test_sends_get_to_correct_path(self) -> None:
        transport = AsyncStubTransport(response=_ok({"providers": []}))
        api = _make_async_api(transport)
        await api.get_providers()
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/providers"

    @pytest.mark.anyio
    async def test_sends_oms_id_query_param(self) -> None:
        transport = AsyncStubTransport(response=_ok({"providers": []}))
        api = _make_async_api(transport)
        await api.get_providers()
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    @pytest.mark.anyio
    async def test_sends_auth_header(self) -> None:
        transport = AsyncStubTransport(response=_ok({"providers": []}))
        api = _make_async_api(transport, token=_TOKEN)
        await api.get_providers()
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN


# ---------------------------------------------------------------------------
# Async get_quality
# ---------------------------------------------------------------------------


class TestAsyncGetQuality:
    @pytest.mark.anyio
    async def test_returns_quality_response(self) -> None:
        transport = AsyncStubTransport(
            response=_ok({"orderId": _ORDER_ID, "bufferStatus": "ACTIVE"})
        )
        api = _make_async_api(transport)
        result = await api.get_quality(_ORDER_ID)
        assert isinstance(result, QualityResponse)
        assert result.order_id == _ORDER_ID
        assert result.buffer_status == "ACTIVE"

    @pytest.mark.anyio
    async def test_sends_get_to_correct_path(self) -> None:
        transport = AsyncStubTransport(
            response=_ok({"orderId": _ORDER_ID, "bufferStatus": "ACTIVE"})
        )
        api = _make_async_api(transport)
        await api.get_quality(_ORDER_ID)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/quality"

    @pytest.mark.anyio
    async def test_sends_required_params(self) -> None:
        transport = AsyncStubTransport(
            response=_ok({"orderId": _ORDER_ID, "bufferStatus": "PENDING"})
        )
        api = _make_async_api(transport)
        await api.get_quality(_ORDER_ID)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("orderId") == _ORDER_ID

    @pytest.mark.anyio
    async def test_sends_auth_header(self) -> None:
        transport = AsyncStubTransport(
            response=_ok({"orderId": _ORDER_ID, "bufferStatus": "ACTIVE"})
        )
        api = _make_async_api(transport, token=_TOKEN)
        await api.get_quality(_ORDER_ID)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    @pytest.mark.anyio
    async def test_extra_fields_preserved(self) -> None:
        transport = AsyncStubTransport(
            response=_ok(
                {
                    "orderId": _ORDER_ID,
                    "bufferStatus": "ACTIVE",
                    "extraKey": "extraVal",
                }
            )
        )
        api = _make_async_api(transport)
        result = await api.get_quality(_ORDER_ID)
        assert result.model_extra is not None
        assert result.model_extra.get("extraKey") == "extraVal"


# ---------------------------------------------------------------------------
# Async get_quality_cis_list
# ---------------------------------------------------------------------------


class TestAsyncGetQualityCisList:
    @pytest.mark.anyio
    async def test_returns_quality_cis_list_response(self) -> None:
        cis_items = [{"cis": "010123456789012321abc"}]
        transport = AsyncStubTransport(
            response=_ok({"totalCount": 1, "results": cis_items})
        )
        api = _make_async_api(transport)
        result = await api.get_quality_cis_list(_ORDER_ID, _GTIN)
        assert isinstance(result, QualityCisListResponse)
        assert result.total_count == 1
        assert result.results == cis_items

    @pytest.mark.anyio
    async def test_sends_get_to_correct_path(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_async_api(transport)
        await api.get_quality_cis_list(_ORDER_ID, _GTIN)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/quality/cisList"

    @pytest.mark.anyio
    async def test_sends_required_params(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_async_api(transport)
        await api.get_quality_cis_list(_ORDER_ID, _GTIN)
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("orderId") == _ORDER_ID
        assert req.params.get("gtin") == _GTIN

    @pytest.mark.anyio
    async def test_sends_optional_limit_and_skip(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_async_api(transport)
        await api.get_quality_cis_list(_ORDER_ID, _GTIN, limit=5, skip=10)
        req = transport.last_request
        assert req is not None
        assert req.params.get("limit") == "5"
        assert req.params.get("skip") == "10"

    @pytest.mark.anyio
    async def test_omits_limit_and_skip_when_none(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_async_api(transport)
        await api.get_quality_cis_list(_ORDER_ID, _GTIN)
        req = transport.last_request
        assert req is not None
        assert "limit" not in req.params
        assert "skip" not in req.params

    @pytest.mark.anyio
    async def test_sends_auth_header(self) -> None:
        transport = AsyncStubTransport(response=_ok({"totalCount": 0, "results": []}))
        api = _make_async_api(transport, token=_TOKEN)
        await api.get_quality_cis_list(_ORDER_ID, _GTIN)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN


# ---------------------------------------------------------------------------
# Async get_mod
# ---------------------------------------------------------------------------


class TestAsyncGetMod:
    @pytest.mark.anyio
    async def test_returns_mod_response(self) -> None:
        transport = AsyncStubTransport(response=_ok({"mod": "SUZ_OMS_v3"}))
        api = _make_async_api(transport)
        result = await api.get_mod()
        assert isinstance(result, ModResponse)
        assert result.mod == "SUZ_OMS_v3"

    @pytest.mark.anyio
    async def test_sends_get_to_correct_path(self) -> None:
        transport = AsyncStubTransport(response=_ok({"mod": "SUZ_OMS_v3"}))
        api = _make_async_api(transport)
        await api.get_mod()
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/mod"

    @pytest.mark.anyio
    async def test_sends_oms_id_query_param(self) -> None:
        transport = AsyncStubTransport(response=_ok({"mod": "SUZ_OMS_v3"}))
        api = _make_async_api(transport)
        await api.get_mod()
        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    @pytest.mark.anyio
    async def test_sends_auth_header(self) -> None:
        transport = AsyncStubTransport(response=_ok({"mod": "SUZ_OMS_v3"}))
        api = _make_async_api(transport, token=_TOKEN)
        await api.get_mod()
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN


# ---------------------------------------------------------------------------
# AsyncSuzClient wiring
# ---------------------------------------------------------------------------


class TestAsyncSuzClientWiring:
    def test_client_has_reference_attribute(self) -> None:
        from suz_sdk.async_client import AsyncSuzClient

        transport = AsyncStubTransport(response=_ok({}))
        client = AsyncSuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        assert isinstance(client.reference, AsyncReferenceApi)

    @pytest.mark.anyio
    async def test_client_reference_get_providers(self) -> None:
        from suz_sdk.async_client import AsyncSuzClient

        transport = AsyncStubTransport(response=_ok({"providers": [{"id": "p1"}]}))
        client = AsyncSuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        result = await client.reference.get_providers()
        assert result.providers == [{"id": "p1"}]
        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    @pytest.mark.anyio
    async def test_client_reference_get_mod(self) -> None:
        from suz_sdk.async_client import AsyncSuzClient

        transport = AsyncStubTransport(response=_ok({"mod": "modX"}))
        client = AsyncSuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=transport)
        result = await client.reference.get_mod()
        assert result.mod == "modX"
