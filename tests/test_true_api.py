"""Tests for TrueApiAuth — the two-step True API authentication flow (§9.3.2)."""

import pytest

from suz_sdk.auth.true_api import TrueApiAuth
from suz_sdk.exceptions import SuzAuthError
from suz_sdk.signing.noop import NoopSigner
from suz_sdk.transport.base import Request, Response


class StubTransport:
    """Stub that cycles through a sequence of responses, one per request."""

    def __init__(self, responses: list[Response | Exception]) -> None:
        self._responses = iter(responses)
        self.requests: list[Request] = []

    def request(self, req: Request) -> Response:
        self.requests.append(req)
        result = next(self._responses)
        if isinstance(result, Exception):
            raise result
        return result


_OMS_CONNECTION = "cdf12109-10d3-11e6-8b6f-0050569977a2"
_CHALLENGE_UUID = "a63ff582-b723-4da7-958b-453da27a6c62"
_CHALLENGE_DATA = "GNUFBAZBMPIUUMLXNMIOGSHT"
_TOKEN = "58f908f1-832a-4ad0-93f4-bdafbf8eb55a"

_AUTH_KEY_RESP = Response(
    status_code=200,
    headers={},
    body={"uuid": _CHALLENGE_UUID, "data": _CHALLENGE_DATA},
)
_TOKEN_RESP = Response(
    status_code=200,
    headers={},
    body={"token": _TOKEN},
)


def _make_auth(transport: StubTransport) -> TrueApiAuth:
    return TrueApiAuth(
        oms_connection=_OMS_CONNECTION,
        signer=NoopSigner(),
        transport=transport,
    )


class TestFetchTokenSuccess:
    def test_returns_token(self) -> None:
        transport = StubTransport([_AUTH_KEY_RESP, _TOKEN_RESP])
        auth = _make_auth(transport)
        token = auth.fetch_token()
        assert token == _TOKEN

    def test_returns_uuid_token_as_fallback(self) -> None:
        uuid_token_resp = Response(
            status_code=200,
            headers={},
            body={"uuidToken": "123e4567-e89b-12d3-a456-426655440000"},
        )
        transport = StubTransport([_AUTH_KEY_RESP, uuid_token_resp])
        auth = _make_auth(transport)
        token = auth.fetch_token()
        assert token == "123e4567-e89b-12d3-a456-426655440000"

    def test_step1_sends_get_auth_key(self) -> None:
        transport = StubTransport([_AUTH_KEY_RESP, _TOKEN_RESP])
        auth = _make_auth(transport)
        auth.fetch_token()

        req1 = transport.requests[0]
        assert req1.method == "GET"
        assert req1.path == "/auth/key"

    def test_step2_sends_post_simple_sign_in(self) -> None:
        transport = StubTransport([_AUTH_KEY_RESP, _TOKEN_RESP])
        auth = _make_auth(transport)
        auth.fetch_token()

        req2 = transport.requests[1]
        assert req2.method == "POST"
        assert req2.path == f"/auth/simpleSignIn/{_OMS_CONNECTION}"

    def test_step2_body_contains_uuid_and_signed_data(self) -> None:
        transport = StubTransport([_AUTH_KEY_RESP, _TOKEN_RESP])
        auth = _make_auth(transport)
        auth.fetch_token()

        req2 = transport.requests[1]
        assert req2.json_body is not None
        assert req2.json_body["uuid"] == _CHALLENGE_UUID
        # NoopSigner signs challenge data bytes as empty string
        assert "data" in req2.json_body

    def test_signer_receives_challenge_data_bytes(self) -> None:
        """The signer must be called with the challenge data bytes."""
        from unittest.mock import MagicMock

        mock_signer = MagicMock()
        mock_signer.sign_bytes.return_value = "signed-data-b64"

        transport = StubTransport([_AUTH_KEY_RESP, _TOKEN_RESP])
        auth = TrueApiAuth(
            oms_connection=_OMS_CONNECTION,
            signer=mock_signer,
            transport=transport,
        )
        auth.fetch_token()

        mock_signer.sign_bytes.assert_called_once_with(_CHALLENGE_DATA.encode())


class TestFetchTokenErrors:
    def test_raises_auth_error_when_no_uuid_in_step1(self) -> None:
        bad_resp = Response(status_code=200, headers={}, body={"data": _CHALLENGE_DATA})
        transport = StubTransport([bad_resp])
        auth = _make_auth(transport)
        with pytest.raises(SuzAuthError, match="uuid"):
            auth.fetch_token()

    def test_raises_auth_error_when_no_data_in_step1(self) -> None:
        bad_resp = Response(status_code=200, headers={}, body={"uuid": _CHALLENGE_UUID})
        transport = StubTransport([bad_resp])
        auth = _make_auth(transport)
        with pytest.raises(SuzAuthError, match="data"):
            auth.fetch_token()

    def test_raises_auth_error_when_no_token_in_step2(self) -> None:
        no_token_resp = Response(status_code=200, headers={}, body={"code": "error"})
        transport = StubTransport([_AUTH_KEY_RESP, no_token_resp])
        auth = _make_auth(transport)
        with pytest.raises(SuzAuthError, match="no token"):
            auth.fetch_token()

    def test_propagates_transport_error_from_step1(self) -> None:
        from suz_sdk.exceptions import SuzTransportError

        transport = StubTransport([SuzTransportError("network failure")])
        auth = _make_auth(transport)
        with pytest.raises(SuzTransportError):
            auth.fetch_token()

    def test_propagates_auth_error_from_step2(self) -> None:
        transport = StubTransport([_AUTH_KEY_RESP, SuzAuthError("unauthorized")])
        auth = _make_auth(transport)
        with pytest.raises(SuzAuthError):
            auth.fetch_token()


class TestAuthApiIntegration:
    """Smoke-test AuthApi.authenticate() wrapper."""

    def test_authenticate_calls_token_manager(self) -> None:
        from unittest.mock import MagicMock
        from suz_sdk.auth.auth_api import AuthApi
        from suz_sdk.auth.token_manager import TokenManager

        mock_tm = MagicMock(spec=TokenManager)
        mock_tm.authenticate.return_value = "auto-tok"
        api = AuthApi(token_manager=mock_tm)
        token = api.authenticate()
        assert token == "auto-tok"
        mock_tm.authenticate.assert_called_once()

    def test_authenticate_raises_when_no_token_manager(self) -> None:
        from suz_sdk.auth.auth_api import AuthApi
        from suz_sdk.exceptions import SuzError

        api = AuthApi(token_manager=None)
        with pytest.raises(SuzError, match="not configured"):
            api.authenticate()
