"""Tests for IntegrationApi.register_connection() (§9.2).

Uses a stub transport to isolate the API logic from HTTP mechanics.
"""

import json

import pytest

from suz_sdk.api.integration import IntegrationApi, RegisterConnectionResponse
from suz_sdk.exceptions import SuzApiError, SuzSignatureError, SuzValidationError
from suz_sdk.signing.noop import NoopSigner
from suz_sdk.transport.base import Request, Response


class StubTransport:
    """Configurable stub that records the last request and returns a preset response."""

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
_OMS_CONNECTION = "cdf12109-10d3-11e6-8b6f-0050569977a2"
_REG_KEY = "4344d884-7f21-456c-981e-cd68e92391e8"

_SUCCESS_BODY = {
    "status": "SUCCESS",
    "omsConnection": _OMS_CONNECTION,
    "name": "ERP Connector",
}
_REJECTED_BODY = {
    "status": "REJECTED",
    "rejectionReason": "Duplicate installation name",
}


def _make_api(
    transport: StubTransport,
    signer: object | None = None,
    registration_key: str | None = _REG_KEY,
) -> IntegrationApi:
    return IntegrationApi(
        transport=transport,
        oms_id=_OMS_ID,
        signer=signer,  # type: ignore[arg-type]
        registration_key=registration_key,
    )


class TestRegisterConnectionSuccess:
    def test_returns_response_model(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport)
        result = api.register_connection(address="г.Москва, ул.1")

        assert isinstance(result, RegisterConnectionResponse)
        assert result.status == "SUCCESS"
        assert result.oms_connection == _OMS_CONNECTION
        assert result.name == "ERP Connector"
        assert result.rejection_reason is None

    def test_returns_rejected_response(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_REJECTED_BODY)
        )
        api = _make_api(transport)
        result = api.register_connection(address="г.Москва, ул.2")

        assert result.status == "REJECTED"
        assert result.rejection_reason == "Duplicate installation name"
        assert result.oms_connection is None

    def test_sends_post_to_correct_path(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport)
        api.register_connection(address="addr")

        req = transport.last_request
        assert req is not None
        assert req.method == "POST"
        assert req.path == "/api/v3/integration/connection"

    def test_sends_oms_id_as_query_param(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport)
        api.register_connection(address="addr")

        req = transport.last_request
        assert req is not None
        assert req.params.get("omsId") == _OMS_ID

    def test_sends_registration_key_header(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport, registration_key=_REG_KEY)
        api.register_connection(address="addr")

        req = transport.last_request
        assert req is not None
        assert req.headers.get("X-RegistrationKey") == _REG_KEY

    def test_no_registration_key_omits_header(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport, registration_key=None)
        api.register_connection(address="addr")

        req = transport.last_request
        assert req is not None
        assert "X-RegistrationKey" not in req.headers

    def test_sends_raw_body_bytes(self) -> None:
        """Body must be pre-serialized bytes (so signature covers exact payload)."""
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport)
        api.register_connection(address="г.Москва, ул.1", name="ERP")

        req = transport.last_request
        assert req is not None
        assert req.raw_body is not None
        body = json.loads(req.raw_body.decode())
        assert body["address"] == "г.Москва, ул.1"
        assert body["name"] == "ERP"

    def test_omits_name_when_not_provided(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport)
        api.register_connection(address="addr")

        req = transport.last_request
        assert req is not None
        body = json.loads(req.raw_body.decode())  # type: ignore[union-attr]
        assert "name" not in body

    def test_sends_content_type_json_header(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport)
        api.register_connection(address="addr")

        req = transport.last_request
        assert req is not None
        assert req.headers.get("Content-Type") == "application/json"

    def test_signs_body_when_signer_provided(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport, signer=NoopSigner())
        api.register_connection(address="addr")

        req = transport.last_request
        assert req is not None
        # NoopSigner returns "", so X-Signature header is present (even if empty)
        assert "X-Signature" in req.headers

    def test_no_signature_header_without_signer(self) -> None:
        transport = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        api = _make_api(transport, signer=None)
        api.register_connection(address="addr")

        req = transport.last_request
        assert req is not None
        assert "X-Signature" not in req.headers


class TestRegisterConnectionErrors:
    def test_propagates_signature_error(self) -> None:
        transport = StubTransport(exc=SuzSignatureError("attached signature rejected"))
        api = _make_api(transport)
        with pytest.raises(SuzSignatureError):
            api.register_connection(address="addr")

    def test_propagates_validation_error(self) -> None:
        transport = StubTransport(exc=SuzValidationError("invalid address"))
        api = _make_api(transport)
        with pytest.raises(SuzValidationError):
            api.register_connection(address="")

    def test_propagates_api_error(self) -> None:
        transport = StubTransport(exc=SuzApiError("server error", status_code=500))
        api = _make_api(transport)
        with pytest.raises(SuzApiError):
            api.register_connection(address="addr")


class TestSuzClientIntegrationWiring:
    """Smoke-test that SuzClient wires IntegrationApi correctly."""

    def test_client_integration_is_available(self) -> None:
        from suz_sdk.client import SuzClient
        from suz_sdk.api.integration import IntegrationApi

        client = SuzClient(oms_id=_OMS_ID, registration_key=_REG_KEY)
        assert isinstance(client.integration, IntegrationApi)

    def test_client_integration_uses_main_transport(self) -> None:
        from suz_sdk.client import SuzClient

        stub = StubTransport(
            response=Response(status_code=200, headers={}, body=_SUCCESS_BODY)
        )
        client = SuzClient(oms_id=_OMS_ID, registration_key=_REG_KEY, transport=stub)
        result = client.integration.register_connection(address="addr")

        assert result.status == "SUCCESS"
        assert stub.last_request is not None
