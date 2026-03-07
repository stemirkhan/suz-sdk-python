"""Tests for RetryConfig and retry behaviour in HttpxTransport / AsyncHttpxTransport."""

from unittest.mock import patch

import pytest

from suz_sdk.exceptions import SuzApiError, SuzTimeoutError, SuzTransportError
from suz_sdk.transport.base import Request
from suz_sdk.transport.httpx_transport import HttpxTransport
from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport
from suz_sdk.transport.retry import RetryConfig

BASE_URL = "https://suz-retry-test.example.com"

_GET_REQ = Request(method="GET", path="/api/v3/ping", params={"omsId": "abc"})
_GET_URL = f"{BASE_URL}/api/v3/ping?omsId=abc"


# ---------------------------------------------------------------------------
# RetryConfig — defaults and structure
# ---------------------------------------------------------------------------


class TestRetryConfigDefaults:
    def test_max_retries_default(self):
        assert RetryConfig().max_retries == 3

    def test_backoff_factor_default(self):
        assert RetryConfig().backoff_factor == 0.5

    def test_retry_statuses_default(self):
        assert RetryConfig().retry_statuses == frozenset({500, 502, 503, 504})

    def test_retry_on_network_errors_default(self):
        assert RetryConfig().retry_on_network_errors is True

    def test_custom_values(self):
        cfg = RetryConfig(max_retries=1, backoff_factor=1.0, retry_statuses=frozenset({503}))
        assert cfg.max_retries == 1
        assert cfg.backoff_factor == 1.0
        assert cfg.retry_statuses == frozenset({503})

    def test_exported_from_package(self):
        from suz_sdk import RetryConfig as Imported
        assert Imported is RetryConfig


# ---------------------------------------------------------------------------
# HttpxTransport — no retry by default
# ---------------------------------------------------------------------------


class TestNoRetryByDefault:
    def test_500_raises_immediately_without_retry(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"globalErrors": [{"error": "Server error", "errorCode": "500"}]},
            status_code=500,
        )
        t = HttpxTransport(base_url=BASE_URL)
        with pytest.raises(SuzApiError):
            t.request(_GET_REQ)
        t.close()

    def test_only_one_attempt_without_retry(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET", url=_GET_URL, json={}, status_code=500,
        )
        t = HttpxTransport(base_url=BASE_URL)
        with pytest.raises(SuzApiError):
            t.request(_GET_REQ)
        # httpx_mock raises if there are unused responses — one response = one attempt
        t.close()


# ---------------------------------------------------------------------------
# HttpxTransport — retry on 5xx
# ---------------------------------------------------------------------------


class TestRetryOn5xx:
    def test_retries_on_500_and_succeeds(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET", url=_GET_URL, json={}, status_code=500,
        )
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"omsId": "abc", "apiVersion": "3", "omsVersion": "4"},
            status_code=200,
        )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=1, backoff_factor=0))
        with patch("time.sleep"):
            resp = t.request(_GET_REQ)
        assert resp.status_code == 200
        t.close()

    def test_raises_after_all_retries_exhausted(self, httpx_mock) -> None:
        for _ in range(4):  # 1 attempt + 3 retries
            httpx_mock.add_response(
                method="GET", url=_GET_URL, json={}, status_code=500,
            )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=3, backoff_factor=0))
        with patch("time.sleep"), pytest.raises(SuzApiError) as exc_info:
            t.request(_GET_REQ)
        assert exc_info.value.status_code == 500
        t.close()

    def test_does_not_retry_on_400(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"globalErrors": [{"error": "Bad input", "errorCode": "400"}]},
            status_code=400,
        )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=3, backoff_factor=0))
        with patch("time.sleep"):
            from suz_sdk.exceptions import SuzValidationError
            with pytest.raises(SuzValidationError):
                t.request(_GET_REQ)
        t.close()

    def test_does_not_retry_on_401(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"globalErrors": [{"error": "Unauthorized", "errorCode": "401"}]},
            status_code=401,
        )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=3, backoff_factor=0))
        with patch("time.sleep"):
            from suz_sdk.exceptions import SuzAuthError
            with pytest.raises(SuzAuthError):
                t.request(_GET_REQ)
        t.close()

    def test_retry_only_on_configured_statuses(self, httpx_mock) -> None:
        # 404 is not in retry_statuses by default — should not be retried
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"globalErrors": [{"error": "Not found", "errorCode": "404"}]},
            status_code=404,
        )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=3, backoff_factor=0))
        with patch("time.sleep"), pytest.raises(SuzApiError) as exc_info:
            t.request(_GET_REQ)
        assert exc_info.value.status_code == 404
        t.close()


# ---------------------------------------------------------------------------
# HttpxTransport — retry on network errors
# ---------------------------------------------------------------------------


class TestRetryOnNetworkErrors:
    def test_retries_on_timeout_and_succeeds(self, httpx_mock) -> None:
        import httpx as _httpx
        httpx_mock.add_exception(
            _httpx.ReadTimeout("timed out"), url=_GET_URL,
        )
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"omsId": "abc", "apiVersion": "3", "omsVersion": "4"},
            status_code=200,
        )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=1, backoff_factor=0))
        with patch("time.sleep"):
            resp = t.request(_GET_REQ)
        assert resp.status_code == 200
        t.close()

    def test_raises_timeout_after_all_retries(self, httpx_mock) -> None:
        import httpx as _httpx
        for _ in range(2):
            httpx_mock.add_exception(_httpx.ReadTimeout("timed out"), url=_GET_URL)
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=1, backoff_factor=0))
        with patch("time.sleep"), pytest.raises(SuzTimeoutError):
            t.request(_GET_REQ)
        t.close()

    def test_no_network_retry_when_disabled(self, httpx_mock) -> None:
        import httpx as _httpx
        httpx_mock.add_exception(_httpx.ConnectError("refused"), url=_GET_URL)
        cfg = RetryConfig(max_retries=3, backoff_factor=0, retry_on_network_errors=False)
        t = HttpxTransport(base_url=BASE_URL, retry=cfg)
        with patch("time.sleep"), pytest.raises(SuzTransportError):
            t.request(_GET_REQ)
        t.close()


# ---------------------------------------------------------------------------
# HttpxTransport — backoff timing
# ---------------------------------------------------------------------------


class TestBackoffTiming:
    def test_sleep_called_between_retries(self, httpx_mock) -> None:
        for _ in range(3):
            httpx_mock.add_response(method="GET", url=_GET_URL, json={}, status_code=500)
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"omsId": "abc", "apiVersion": "3", "omsVersion": "4"},
            status_code=200,
        )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=3, backoff_factor=0.5))
        sleep_calls = []
        with patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            t.request(_GET_REQ)
        # 3 retries → 3 sleeps
        assert len(sleep_calls) == 3
        t.close()

    def test_backoff_is_exponential(self, httpx_mock) -> None:
        for _ in range(3):
            httpx_mock.add_response(method="GET", url=_GET_URL, json={}, status_code=500)
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"omsId": "abc", "apiVersion": "3", "omsVersion": "4"},
            status_code=200,
        )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=3, backoff_factor=1.0))
        sleep_calls = []
        with patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            t.request(_GET_REQ)
        # 1.0 * 2^0, 1.0 * 2^1, 1.0 * 2^2 → 1.0, 2.0, 4.0
        assert sleep_calls == [1.0, 2.0, 4.0]
        t.close()


# ---------------------------------------------------------------------------
# HttpxTransport — retry warning logs
# ---------------------------------------------------------------------------


class TestRetryLogging:
    def test_warning_logged_on_retry(self, httpx_mock, caplog) -> None:
        import logging
        httpx_mock.add_response(method="GET", url=_GET_URL, json={}, status_code=500)
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"omsId": "abc", "apiVersion": "3", "omsVersion": "4"},
            status_code=200,
        )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=1, backoff_factor=0))
        with patch("time.sleep"), caplog.at_level(logging.WARNING, logger="suz_sdk"):
            t.request(_GET_REQ)
        assert any("Retry" in r.message for r in caplog.records)
        t.close()

    def test_warning_contains_status_code(self, httpx_mock, caplog) -> None:
        import logging
        httpx_mock.add_response(method="GET", url=_GET_URL, json={}, status_code=503)
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"omsId": "abc", "apiVersion": "3", "omsVersion": "4"},
            status_code=200,
        )
        t = HttpxTransport(base_url=BASE_URL, retry=RetryConfig(max_retries=1, backoff_factor=0))
        with patch("time.sleep"), caplog.at_level(logging.WARNING, logger="suz_sdk"):
            t.request(_GET_REQ)
        assert any("503" in r.message for r in caplog.records)
        t.close()


# ---------------------------------------------------------------------------
# AsyncHttpxTransport — retry on 5xx
# ---------------------------------------------------------------------------


class TestAsyncRetryOn5xx:
    @pytest.mark.anyio
    async def test_retries_on_500_and_succeeds(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET", url=_GET_URL, json={}, status_code=500,
        )
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"omsId": "abc", "apiVersion": "3", "omsVersion": "4"},
            status_code=200,
        )
        t = AsyncHttpxTransport(
            base_url=BASE_URL, retry=RetryConfig(max_retries=1, backoff_factor=0)
        )
        with patch("asyncio.sleep"):
            resp = await t.request(_GET_REQ)
        assert resp.status_code == 200
        await t.aclose()

    @pytest.mark.anyio
    async def test_raises_after_all_retries_exhausted(self, httpx_mock) -> None:
        for _ in range(2):
            httpx_mock.add_response(method="GET", url=_GET_URL, json={}, status_code=500)
        t = AsyncHttpxTransport(
            base_url=BASE_URL, retry=RetryConfig(max_retries=1, backoff_factor=0)
        )
        with patch("asyncio.sleep"):
            with pytest.raises(SuzApiError) as exc_info:
                await t.request(_GET_REQ)
        assert exc_info.value.status_code == 500
        await t.aclose()

    @pytest.mark.anyio
    async def test_does_not_retry_on_400(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"globalErrors": [{"error": "Bad input", "errorCode": "400"}]},
            status_code=400,
        )
        t = AsyncHttpxTransport(
            base_url=BASE_URL, retry=RetryConfig(max_retries=3, backoff_factor=0)
        )
        with patch("asyncio.sleep"):
            from suz_sdk.exceptions import SuzValidationError
            with pytest.raises(SuzValidationError):
                await t.request(_GET_REQ)
        await t.aclose()

    @pytest.mark.anyio
    async def test_backoff_sleep_called(self, httpx_mock) -> None:
        for _ in range(2):
            httpx_mock.add_response(method="GET", url=_GET_URL, json={}, status_code=500)
        httpx_mock.add_response(
            method="GET", url=_GET_URL,
            json={"omsId": "abc", "apiVersion": "3", "omsVersion": "4"},
            status_code=200,
        )
        t = AsyncHttpxTransport(
            base_url=BASE_URL, retry=RetryConfig(max_retries=2, backoff_factor=1.0)
        )
        sleep_calls: list[float] = []
        with patch("asyncio.sleep", side_effect=lambda s: sleep_calls.append(s)):
            await t.request(_GET_REQ)
        assert sleep_calls == [1.0, 2.0]
        await t.aclose()
