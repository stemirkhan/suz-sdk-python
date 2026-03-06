"""No-op signer for testing and development.

WARNING: NoopSigner produces an empty signature string.  The СУЗ server
will reject requests that require a valid X-Signature.  Use this signer
only in scenarios where signing is optional or in unit tests that mock
the HTTP transport.

For real integrations, supply a CMS-compatible signer based on CryptoPro
or another GOST-compliant library.
"""


class NoopSigner:
    """Signer that returns an empty string instead of a real CMS signature.

    Satisfies the BaseSigner Protocol and is safe to use as a default in
    unit tests and local development where the X-Signature header is not
    validated.
    """

    def sign_bytes(self, payload: bytes) -> str:
        """Return an empty string (no actual signing performed).

        Args:
            payload: Ignored.

        Returns:
            Empty string.
        """
        return ""
