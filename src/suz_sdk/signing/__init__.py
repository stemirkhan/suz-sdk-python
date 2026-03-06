"""Signing abstractions for the SUZ SDK.

The SDK never hard-codes a specific cryptographic tool.  Callers supply a
signer that implements the BaseSigner Protocol and the SDK passes it the
raw bytes to sign.

Supported by the API (§2.3.1):
- Detached CMS signature (IETF RFC 5652)
- Russian GOST algorithms: GOST 28147-89, GOST R 34.10-2012, GOST R 34.11-2012
- Signature placed in X-Signature HTTP header, Base64-encoded
- Attached signatures are NOT supported (server returns HTTP 413)
"""

from suz_sdk.signing.base import BaseSigner
from suz_sdk.signing.noop import NoopSigner

__all__ = ["BaseSigner", "NoopSigner"]
