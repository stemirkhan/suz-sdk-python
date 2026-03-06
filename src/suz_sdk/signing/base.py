"""Base signer Protocol for the SUZ SDK.

The signing contract is deliberately minimal.  All cryptographic complexity
(key loading, certificate handling, GOST algorithm selection) lives in the
concrete signer implementation — not here.

Signing rules per API specification (§2.3.1):
- Signature format: detached CMS (IETF RFC 5652), Base64-encoded
- For GET requests: sign REQUEST_PATH + QUERY_STRING
  Example: /api/v3/ping?omsId=cdf12109-...
- For POST requests: sign the raw JSON request body bytes
- Attached signatures are rejected (HTTP 413)
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class BaseSigner(Protocol):
    """Protocol for request signers.

    Any object that implements ``sign_bytes`` can be used as a signer.
    The SDK passes raw bytes and expects a Base64-encoded detached CMS
    signature string in return.

    Example implementations:
    - NoopSigner   — for testing (returns empty string, no real signature)
    - CryptoProSigner — wraps a CryptoPro CLI tool or library
    - ExternalSigner  — delegates to an external signing service
    """

    def sign_bytes(self, payload: bytes) -> str:
        """Sign payload bytes and return a Base64-encoded detached CMS signature.

        Args:
            payload: Raw bytes to sign.
                     For GET: encode the path+query string (UTF-8).
                     For POST: encode the JSON body (UTF-8, compact, sorted keys).

        Returns:
            Base64-encoded detached CMS signature string, suitable for
            placement in the X-Signature HTTP header.

        Raises:
            Any exception from the underlying crypto library.  The SDK will
            not swallow signing errors.
        """
        ...
