"""Tests for IntegrationApi.get_uot_profile and AsyncIntegrationApi.get_uot_profile.

Covers:
  - HTTP method and path correctness
  - Uses Authorization: Bearer header (NOT clientToken)
  - Response model field mapping
  - Defaults when optional fields are missing
"""

import pytest

from suz_sdk.api.async_integration import AsyncIntegrationApi
from suz_sdk.api.integration import IntegrationApi, UotProfileResponse
from suz_sdk.transport.base import Request, Response

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_OMS_ID = "cdf12109-10d3-11e6-8b6f-0050569977a1"
_REG_KEY = "4344d884-7f21-456c-981e-cd68e92391e8"
_BEARER_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"

_FULL_PROFILE_RESP = {
    "omsId": _OMS_ID,
    "profileStatus": "ACTIVE",
    "productGroups": ["milk", "shoes"],
    "lockedProductGroups": ["tobacco"],
    "blockedProductGroups": [],
}

# ---------------------------------------------------------------------------
# Stub transports
# ---------------------------------------------------------------------------


class StubTransport:
    """Records the last request and returns a preset Response."""

    def __init__(self, response: Response | None = None) -> None:
        self._response = response
        self.last_request: Request | None = None

    def request(self, req: Request) -> Response:
        self.last_request = req
        assert self._response is not None
        return self._response


class AsyncStubTransport:
    """Async stub transport."""

    def __init__(self, response: Response | None = None) -> None:
        self._response = response
        self.last_request: Request | None = None

    async def request(self, req: Request) -> Response:
        self.last_request = req
        assert self._response is not None
        return self._response

    async def aclose(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_api(transport: StubTransport) -> IntegrationApi:
    return IntegrationApi(
        transport=transport,
        oms_id=_OMS_ID,
        signer=None,
        registration_key=_REG_KEY,
        get_auth_headers=lambda: {"clientToken": "tok"},
    )


def _make_async_api(transport: AsyncStubTransport) -> AsyncIntegrationApi:
    async def get_auth_headers() -> dict[str, str]:
        return {"clientToken": "tok"}

    return AsyncIntegrationApi(
        transport=transport,
        oms_id=_OMS_ID,
        signer=None,
        registration_key=_REG_KEY,
        get_auth_headers=get_auth_headers,
    )


def _ok(body: object) -> Response:
    return Response(status_code=200, headers={}, body=body)


# ---------------------------------------------------------------------------
# get_uot_profile — sync
# ---------------------------------------------------------------------------


class TestGetUotProfile:
    def test_returns_uot_profile_response(self) -> None:
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert isinstance(result, UotProfileResponse)

    def test_oms_id_field(self) -> None:
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.oms_id == _OMS_ID

    def test_profile_status_field(self) -> None:
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.profile_status == "ACTIVE"

    def test_product_groups_field(self) -> None:
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.product_groups == ["milk", "shoes"]

    def test_locked_product_groups_field(self) -> None:
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.locked_product_groups == ["tobacco"]

    def test_blocked_product_groups_field(self) -> None:
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.blocked_product_groups == []

    def test_sends_get_to_correct_path(self) -> None:
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/integration/profile"

    def test_uses_authorization_bearer_header(self) -> None:
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Authorization") == f"Bearer {_BEARER_TOKEN}"

    def test_does_not_use_client_token_header(self) -> None:
        """get_uot_profile must NOT inject the usual clientToken auth header."""
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        req = transport.last_request
        assert req is not None
        assert "clientToken" not in req.headers

    def test_sends_accept_json_header(self) -> None:
        transport = StubTransport(response=_ok(_FULL_PROFILE_RESP))
        _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Accept") == "application/json"

    def test_optional_fields_default_to_none_and_empty(self) -> None:
        transport = StubTransport(response=_ok({}))
        result = _make_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.oms_id is None
        assert result.profile_status is None
        assert result.product_groups == []
        assert result.locked_product_groups == []
        assert result.blocked_product_groups == []

    def test_bearer_token_is_embedded_in_header_value(self) -> None:
        custom_token = "my.custom.jwt"
        transport = StubTransport(response=_ok({}))
        _make_api(transport).get_uot_profile(custom_token)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Authorization") == f"Bearer {custom_token}"


# ---------------------------------------------------------------------------
# get_uot_profile — async
# ---------------------------------------------------------------------------


class TestAsyncGetUotProfile:
    @pytest.mark.anyio
    async def test_returns_uot_profile_response(self) -> None:
        transport = AsyncStubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = await _make_async_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert isinstance(result, UotProfileResponse)

    @pytest.mark.anyio
    async def test_oms_id_field(self) -> None:
        transport = AsyncStubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = await _make_async_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.oms_id == _OMS_ID

    @pytest.mark.anyio
    async def test_profile_status_field(self) -> None:
        transport = AsyncStubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = await _make_async_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.profile_status == "ACTIVE"

    @pytest.mark.anyio
    async def test_product_groups_field(self) -> None:
        transport = AsyncStubTransport(response=_ok(_FULL_PROFILE_RESP))
        result = await _make_async_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.product_groups == ["milk", "shoes"]

    @pytest.mark.anyio
    async def test_sends_get_to_correct_path(self) -> None:
        transport = AsyncStubTransport(response=_ok(_FULL_PROFILE_RESP))
        await _make_async_api(transport).get_uot_profile(_BEARER_TOKEN)
        req = transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert req.path == "/api/v3/integration/profile"

    @pytest.mark.anyio
    async def test_uses_authorization_bearer_header(self) -> None:
        transport = AsyncStubTransport(response=_ok(_FULL_PROFILE_RESP))
        await _make_async_api(transport).get_uot_profile(_BEARER_TOKEN)
        req = transport.last_request
        assert req is not None
        assert req.headers.get("Authorization") == f"Bearer {_BEARER_TOKEN}"

    @pytest.mark.anyio
    async def test_does_not_use_client_token_header(self) -> None:
        transport = AsyncStubTransport(response=_ok(_FULL_PROFILE_RESP))
        await _make_async_api(transport).get_uot_profile(_BEARER_TOKEN)
        req = transport.last_request
        assert req is not None
        assert "clientToken" not in req.headers

    @pytest.mark.anyio
    async def test_optional_fields_default_to_none_and_empty(self) -> None:
        transport = AsyncStubTransport(response=_ok({}))
        result = await _make_async_api(transport).get_uot_profile(_BEARER_TOKEN)
        assert result.oms_id is None
        assert result.profile_status is None
        assert result.product_groups == []
        assert result.locked_product_groups == []
        assert result.blocked_product_groups == []
