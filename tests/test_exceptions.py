"""Tests for the SDK exception hierarchy."""

from suz_sdk.exceptions import (
    SuzApiError,
    SuzAuthError,
    SuzError,
    SuzSignatureError,
    SuzTimeoutError,
    SuzTokenExpiredError,
    SuzTransportError,
    SuzValidationError,
)


class TestExceptionHierarchy:
    """Verify that exceptions inherit correctly for broad/narrow catching."""

    def test_transport_error_is_suz_error(self) -> None:
        assert issubclass(SuzTransportError, SuzError)

    def test_timeout_error_is_transport_error(self) -> None:
        assert issubclass(SuzTimeoutError, SuzTransportError)

    def test_timeout_error_is_suz_error(self) -> None:
        assert issubclass(SuzTimeoutError, SuzError)

    def test_auth_error_is_suz_error(self) -> None:
        assert issubclass(SuzAuthError, SuzError)

    def test_token_expired_is_auth_error(self) -> None:
        assert issubclass(SuzTokenExpiredError, SuzAuthError)

    def test_signature_error_is_suz_error(self) -> None:
        assert issubclass(SuzSignatureError, SuzError)

    def test_validation_error_is_suz_error(self) -> None:
        assert issubclass(SuzValidationError, SuzError)

    def test_api_error_is_suz_error(self) -> None:
        assert issubclass(SuzApiError, SuzError)


class TestSuzApiError:
    def test_attributes_stored(self) -> None:
        err = SuzApiError(
            message="operation failed",
            status_code=500,
            error_code="1010",
            raw_body={"success": False},
        )
        assert str(err) == "operation failed"
        assert err.status_code == 500
        assert err.error_code == "1010"
        assert err.raw_body == {"success": False}

    def test_optional_attributes_default_to_none(self) -> None:
        err = SuzApiError("oops", status_code=404)
        assert err.error_code is None
        assert err.raw_body is None

    def test_repr_contains_status_code(self) -> None:
        err = SuzApiError("bad request", status_code=400, error_code="42")
        assert "400" in repr(err)
        assert "42" in repr(err)

    def test_can_be_caught_as_suz_error(self) -> None:
        try:
            raise SuzApiError("fail", status_code=500)
        except SuzError:
            pass  # expected

    def test_timeout_can_be_caught_as_transport(self) -> None:
        try:
            raise SuzTimeoutError("timed out")
        except SuzTransportError:
            pass  # expected
