"""Tests for signing abstractions."""

from suz_sdk.signing.base import BaseSigner
from suz_sdk.signing.noop import NoopSigner


class TestNoopSigner:
    def test_returns_empty_string(self) -> None:
        signer = NoopSigner()
        result = signer.sign_bytes(b"some payload")
        assert result == ""

    def test_accepts_empty_bytes(self) -> None:
        signer = NoopSigner()
        result = signer.sign_bytes(b"")
        assert result == ""

    def test_satisfies_base_signer_protocol(self) -> None:
        """NoopSigner must satisfy the BaseSigner Protocol for runtime checks."""
        signer = NoopSigner()
        assert isinstance(signer, BaseSigner)

    def test_custom_signer_satisfies_protocol(self) -> None:
        """Any object with sign_bytes satisfies the Protocol."""

        class MySigner:
            def sign_bytes(self, payload: bytes) -> str:
                return "base64signaturehere"

        signer = MySigner()
        assert isinstance(signer, BaseSigner)

    def test_object_without_sign_bytes_fails_protocol(self) -> None:
        class BadSigner:
            pass

        assert not isinstance(BadSigner(), BaseSigner)
