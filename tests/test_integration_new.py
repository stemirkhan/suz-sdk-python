"""Tests for new IntegrationApi methods: list_connections, delete_connection."""

import pytest

from suz_sdk.api.integration import (
    ConnectionInfo,
    DeleteConnectionResponse,
    IntegrationApi,
    ListConnectionsResponse,
)
from suz_sdk.transport.base import Request, Response


_OMS_ID = "cdf12109-10d3-11e6-8b6f-0050569977a1"
_OMS_CONNECTION = "aabb1234-5678-90ab-cdef-1234567890ab"
_REG_KEY = "4344d884-7f21-456c-981e-cd68e92391e8"

_CONNECTION_INFO = {
    "omsConnection": _OMS_CONNECTION,
    "address": "г.Москва, ул.Ленина 1",
    "programName": "ERP",
    "productGroups": ["milk", "shoes"],
    "productVersion": "1.0.0",
    "vendorInn": "1234567890",
}

_LIST_CONNECTIONS_RESP = {
    "omsConnectionInfos": [_CONNECTION_INFO],
    "total": 1,
}

_DELETE_RESP = {"success": True}


class StubTransport:
    def __init__(self, response: Response | None = None) -> None:
        self._response = response
        self.last_request: Request | None = None

    def request(self, req: Request) -> Response:
        self.last_request = req
        assert self._response is not None
        return self._response


def _make_api(transport: StubTransport) -> IntegrationApi:
    return IntegrationApi(
        transport=transport,
        oms_id=_OMS_ID,
        signer=None,
        registration_key=_REG_KEY,
        get_auth_headers=lambda: {"clientToken": "tok"},
    )


# ---------------------------------------------------------------------------
# list_connections()
# ---------------------------------------------------------------------------

class TestListConnections:
    def test_returns_response_model(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_CONNECTIONS_RESP,
        ))
        result = _make_api(transport).list_connections()

        assert isinstance(result, ListConnectionsResponse)
        assert result.total == 1

    def test_parses_connection_info(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_CONNECTIONS_RESP,
        ))
        result = _make_api(transport).list_connections()

        assert len(result.oms_connection_infos) == 1
        conn = result.oms_connection_infos[0]
        assert isinstance(conn, ConnectionInfo)
        assert conn.oms_connection == _OMS_CONNECTION
        assert conn.address == "г.Москва, ул.Ленина 1"
        assert conn.program_name == "ERP"
        assert conn.product_groups == ["milk", "shoes"]
        assert conn.product_version == "1.0.0"
        assert conn.vendor_inn == "1234567890"

    def test_empty_infos_when_missing(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body={"total": 0},
        ))
        result = _make_api(transport).list_connections()

        assert result.oms_connection_infos == []
        assert result.total == 0

    def test_optional_fields_default_to_none(self) -> None:
        minimal_conn = {"omsConnection": _OMS_CONNECTION}
        transport = StubTransport(response=Response(
            status_code=200, headers={},
            body={"omsConnectionInfos": [minimal_conn], "total": 1},
        ))
        result = _make_api(transport).list_connections()

        conn = result.oms_connection_infos[0]
        assert conn.address is None
        assert conn.program_name is None
        assert conn.product_groups == []
        assert conn.product_version is None
        assert conn.vendor_inn is None

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_CONNECTIONS_RESP,
        ))
        _make_api(transport).list_connections()

        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/integration/connection"

    def test_sends_correct_query_params_defaults(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_CONNECTIONS_RESP,
        ))
        _make_api(transport).list_connections()

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("limit") == "10"
        assert req.params.get("offset") == "0"

    def test_sends_custom_limit_and_offset(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_CONNECTIONS_RESP,
        ))
        _make_api(transport).list_connections(limit=25, offset=50)

        req = transport.last_request
        assert req is not None
        assert req.params.get("limit") == "25"
        assert req.params.get("offset") == "50"

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_CONNECTIONS_RESP,
        ))
        _make_api(transport).list_connections()

        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == "tok"


# ---------------------------------------------------------------------------
# delete_connection()
# ---------------------------------------------------------------------------

class TestDeleteConnection:
    def test_returns_response_model(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_DELETE_RESP,
        ))
        result = _make_api(transport).delete_connection(_OMS_CONNECTION)

        assert isinstance(result, DeleteConnectionResponse)
        assert result.success is True

    def test_success_false_when_missing(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body={},
        ))
        result = _make_api(transport).delete_connection(_OMS_CONNECTION)

        assert result.success is False

    def test_sends_delete_to_correct_path(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_DELETE_RESP,
        ))
        _make_api(transport).delete_connection(_OMS_CONNECTION)

        req = transport.last_request
        assert req is not None
        assert req.method == "DELETE"
        assert req.path == "/api/v3/integration/connection"

    def test_sends_correct_query_params(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_DELETE_RESP,
        ))
        _make_api(transport).delete_connection(_OMS_CONNECTION)

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID
        assert req.params.get("omsConnection") == _OMS_CONNECTION

    def test_sends_auth_header(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_DELETE_RESP,
        ))
        _make_api(transport).delete_connection(_OMS_CONNECTION)

        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == "tok"


# ---------------------------------------------------------------------------
# Without get_auth_headers
# ---------------------------------------------------------------------------

class TestWithoutAuthHeaders:
    def test_list_connections_without_auth_headers(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_LIST_CONNECTIONS_RESP,
        ))
        api = IntegrationApi(
            transport=transport,
            oms_id=_OMS_ID,
            signer=None,
            registration_key=_REG_KEY,
        )
        result = api.list_connections()

        assert result.total == 1
        req = transport.last_request
        assert req is not None
        assert "clientToken" not in req.headers

    def test_delete_connection_without_auth_headers(self) -> None:
        transport = StubTransport(response=Response(
            status_code=200, headers={}, body=_DELETE_RESP,
        ))
        api = IntegrationApi(
            transport=transport,
            oms_id=_OMS_ID,
            signer=None,
            registration_key=_REG_KEY,
        )
        result = api.delete_connection(_OMS_CONNECTION)

        assert result.success is True
