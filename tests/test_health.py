"""Tests for the HealthApi.ping() method.

Uses a simple stub transport to avoid httpx dependency in these focused
unit tests.  Transport-level behaviour (error mapping, timeouts) is covered
separately in test_transport.py.
"""

import pytest

from suz_sdk.api.health import HealthApi, PingResponse
from suz_sdk.exceptions import SuzAuthError, SuzApiError
from suz_sdk.transport.base import Request, Response


class StubTransport:
    """Configurable stub that returns a preset Response or raises an exception."""

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


_OMS_ID = "cdf12109-10d3-11e6-8b6f-0050569977a1"
_TOKEN = "1cecc8fb-fb47-4c8a-af3d-d34c1ead8c4f"


def _make_api(transport: StubTransport, token: str | None = _TOKEN) -> HealthApi:
    def get_auth_headers() -> dict[str, str]:
        return {"clientToken": token} if token else {}

    return HealthApi(transport=transport, oms_id=_OMS_ID, get_auth_headers=get_auth_headers)


class TestPingSuccess:
    def test_returns_ping_response(self) -> None:
        transport = StubTransport(
            response=Response(
                status_code=200,
                headers={},
                body={
                    "omsId": _OMS_ID,
                    "apiVersion": "2.0.0.54",
                    "omsVersion": "3.1.8.0",
                },
            )
        )
        api = _make_api(transport)
        result = api.ping()

        assert isinstance(result, PingResponse)
        assert result.oms_id == _OMS_ID
        assert result.api_version == "2.0.0.54"
        assert result.oms_version == "3.1.8.0"

    def test_sends_correct_path_and_method(self) -> None:
        transport = StubTransport(
            response=Response(
                status_code=200,
                headers={},
                body={"omsId": _OMS_ID, "apiVersion": "2.0", "omsVersion": "3.0"},
            )
        )
        api = _make_api(transport)
        api.ping()

        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/ping"

    def test_sends_oms_id_as_query_param(self) -> None:
        transport = StubTransport(
            response=Response(
                status_code=200,
                headers={},
                body={"omsId": _OMS_ID, "apiVersion": "2.0", "omsVersion": "3.0"},
            )
        )
        api = _make_api(transport)
        api.ping()

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    def test_sends_client_token_header(self) -> None:
        transport = StubTransport(
            response=Response(
                status_code=200,
                headers={},
                body={"omsId": _OMS_ID, "apiVersion": "2.0", "omsVersion": "3.0"},
            )
        )
        api = _make_api(transport, token=_TOKEN)
        api.ping()

        req = transport.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN

    def test_no_token_sends_no_client_token_header(self) -> None:
        transport = StubTransport(
            response=Response(
                status_code=200,
                headers={},
                body={"omsId": _OMS_ID, "apiVersion": "2.0", "omsVersion": "3.0"},
            )
        )
        api = _make_api(transport, token=None)
        api.ping()

        req = transport.last_request
        assert req is not None
        assert "clientToken" not in req.headers

    def test_sends_accept_json_header(self) -> None:
        transport = StubTransport(
            response=Response(
                status_code=200,
                headers={},
                body={"omsId": _OMS_ID, "apiVersion": "2.0", "omsVersion": "3.0"},
            )
        )
        api = _make_api(transport)
        api.ping()

        req = transport.last_request
        assert req is not None
        assert req.headers.get("Accept") == "application/json"


class TestPingErrors:
    def test_propagates_auth_error(self) -> None:
        transport = StubTransport(exc=SuzAuthError("token invalid"))
        api = _make_api(transport)
        with pytest.raises(SuzAuthError):
            api.ping()

    def test_propagates_api_error(self) -> None:
        transport = StubTransport(exc=SuzApiError("server error", status_code=500))
        api = _make_api(transport)
        with pytest.raises(SuzApiError):
            api.ping()


class TestSuzClientIntegration:
    """Smoke-test the full SuzClient → HealthApi wiring."""

    def test_client_health_ping_wired_correctly(self) -> None:
        from suz_sdk.client import SuzClient

        stub = StubTransport(
            response=Response(
                status_code=200,
                headers={},
                body={"omsId": _OMS_ID, "apiVersion": "2.0.0.54", "omsVersion": "3.1.8.0"},
            )
        )

        client = SuzClient(
            oms_id=_OMS_ID,
            client_token=_TOKEN,
            transport=stub,
        )

        result = client.health.ping()
        assert result.oms_id == _OMS_ID
        assert result.api_version == "2.0.0.54"

    def test_client_injects_token_into_ping(self) -> None:
        from suz_sdk.client import SuzClient

        stub = StubTransport(
            response=Response(
                status_code=200,
                headers={},
                body={"omsId": _OMS_ID, "apiVersion": "2.0", "omsVersion": "3.0"},
            )
        )

        client = SuzClient(oms_id=_OMS_ID, client_token=_TOKEN, transport=stub)
        client.health.ping()

        req = stub.last_request
        assert req is not None
        assert req.headers.get("clientToken") == _TOKEN
