"""Tests for HttpxTransport error mapping and response parsing.

Uses pytest-httpx to intercept outgoing httpx requests without a real
network connection.
"""

import pytest

from suz_sdk.exceptions import (
    SuzApiError,
    SuzAuthError,
    SuzSignatureError,
    SuzTimeoutError,
    SuzTransportError,
    SuzValidationError,
)
from suz_sdk.transport.base import Request
from suz_sdk.transport.httpx_transport import HttpxTransport

BASE_URL = "https://suz-test.example.com"


@pytest.fixture
def transport(httpx_mock):  # noqa: ANN001
    """HttpxTransport pointed at a fake base URL."""
    t = HttpxTransport(base_url=BASE_URL, timeout=5.0)
    yield t
    t.close()


class TestSuccessfulRequests:
    def test_get_returns_parsed_json(self, transport, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/api/v3/ping?omsId=abc",
            json={"omsId": "abc", "apiVersion": "2.0.0.54", "omsVersion": "3.1.8.0"},
            status_code=200,
        )
        req = Request(
            method="GET",
            path="/api/v3/ping",
            params={"omsId": "abc"},
        )
        resp = transport.request(req)
        assert resp.status_code == 200
        assert resp.body["omsId"] == "abc"
        assert resp.body["apiVersion"] == "2.0.0.54"

    def test_response_body_is_none_for_empty_content(self, transport, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/api/v3/something",
            content=b"",
            status_code=200,
        )
        req = Request(method="GET", path="/api/v3/something")
        resp = transport.request(req)
        assert resp.body is None


class TestErrorMapping:
    """Verify that HTTP error codes map to the correct SDK exceptions."""

    def test_400_raises_validation_error(self, transport, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/api/v3/ping?omsId=abc",
            json={
                "globalErrors": [{"error": "Bad omsId", "errorCode": "400"}],
                "success": False,
            },
            status_code=400,
        )
        req = Request(method="GET", path="/api/v3/ping", params={"omsId": "abc"})
        with pytest.raises(SuzValidationError):
            transport.request(req)

    def test_401_raises_auth_error(self, transport, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/api/v3/ping?omsId=abc",
            json={"globalErrors": [{"error": "Unauthorized", "errorCode": "401"}], "success": False},
            status_code=401,
        )
        req = Request(method="GET", path="/api/v3/ping", params={"omsId": "abc"})
        with pytest.raises(SuzAuthError):
            transport.request(req)

    def test_413_raises_signature_error(self, transport, httpx_mock) -> None:
        httpx_mock.add_response(
            method="POST",
            url=f"{BASE_URL}/api/v3/orders",
            json={"globalErrors": [{"error": "Attached signature", "errorCode": "413"}], "success": False},
            status_code=413,
        )
        req = Request(method="POST", path="/api/v3/orders", json_body={"key": "val"})
        with pytest.raises(SuzSignatureError):
            transport.request(req)

    def test_500_raises_api_error_with_status_code(self, transport, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/api/v3/ping?omsId=abc",
            json={"globalErrors": [{"error": "Server error", "errorCode": "500"}], "success": False},
            status_code=500,
        )
        req = Request(method="GET", path="/api/v3/ping", params={"omsId": "abc"})
        with pytest.raises(SuzApiError) as exc_info:
            transport.request(req)
        assert exc_info.value.status_code == 500

    def test_404_raises_api_error(self, transport, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/api/v3/missing",
            status_code=404,
            json={"globalErrors": [{"error": "Not found", "errorCode": "404"}], "success": False},
        )
        req = Request(method="GET", path="/api/v3/missing")
        with pytest.raises(SuzApiError) as exc_info:
            transport.request(req)
        assert exc_info.value.status_code == 404

    def test_error_code_extracted_from_global_errors(self, transport, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/api/v3/ping?omsId=abc",
            json={
                "globalErrors": [{"error": "Something wrong", "errorCode": "1010"}],
                "success": False,
            },
            status_code=500,
        )
        req = Request(method="GET", path="/api/v3/ping", params={"omsId": "abc"})
        with pytest.raises(SuzApiError) as exc_info:
            transport.request(req)
        assert exc_info.value.error_code == "1010"
        assert "Something wrong" in str(exc_info.value)


class TestNetworkErrors:
    def test_timeout_raises_suz_timeout_error(self, httpx_mock) -> None:
        import httpx as _httpx

        httpx_mock.add_exception(
            _httpx.ReadTimeout("timed out"),
            url=f"{BASE_URL}/api/v3/ping?omsId=abc",
        )
        transport = HttpxTransport(base_url=BASE_URL)
        req = Request(method="GET", path="/api/v3/ping", params={"omsId": "abc"})
        with pytest.raises(SuzTimeoutError):
            transport.request(req)
        transport.close()

    def test_connection_error_raises_suz_transport_error(self, httpx_mock) -> None:
        import httpx as _httpx

        httpx_mock.add_exception(
            _httpx.ConnectError("connection refused"),
            url=f"{BASE_URL}/api/v3/ping?omsId=abc",
        )
        transport = HttpxTransport(base_url=BASE_URL)
        req = Request(method="GET", path="/api/v3/ping", params={"omsId": "abc"})
        with pytest.raises(SuzTransportError):
            transport.request(req)
        transport.close()


class TestContextManager:
    def test_context_manager_closes_transport(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=f"{BASE_URL}/api/v3/ping?omsId=abc",
            json={"omsId": "abc", "apiVersion": "2.0", "omsVersion": "3.0"},
            status_code=200,
        )
        with HttpxTransport(base_url=BASE_URL) as t:
            req = Request(method="GET", path="/api/v3/ping", params={"omsId": "abc"})
            resp = t.request(req)
            assert resp.status_code == 200
        # No assertion needed — just verifying no exception on __exit__
