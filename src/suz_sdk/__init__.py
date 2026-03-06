"""suz-sdk — Python SDK for the СУЗ API 3.0 (СУЗ-Облако 4.0).

Public surface of the package.  Import from here rather than from
sub-modules to keep imports stable as internal structure evolves.

Quick start:
    from suz_sdk import SuzClient, Environment

    # Manual token mode
    client = SuzClient(
        oms_id="cdf12109-10d3-11e6-8b6f-0050569977a1",
        environment=Environment.SANDBOX,
        client_token="your-client-token",
    )

    # Auto token mode (via True API)
    client = SuzClient(
        oms_id="...",
        oms_connection="...",
        signer=MyCryptoProSigner(),
    )
    client.auth.authenticate()

    info = client.health.ping()
    print(info.api_version)
"""

from suz_sdk.api.health import PingResponse
from suz_sdk.api.integration import IntegrationApi, RegisterConnectionResponse
from suz_sdk.auth.auth_api import AuthApi
from suz_sdk.auth.token_manager import TokenManager
from suz_sdk.auth.true_api import TrueApiAuth
from suz_sdk.client import SuzClient
from suz_sdk.config import Environment, SuzConfig
from suz_sdk.exceptions import (
    SuzApiError,
    SuzAuthError,
    SuzError,
    SuzRateLimitError,
    SuzSignatureError,
    SuzTimeoutError,
    SuzTokenExpiredError,
    SuzTransportError,
    SuzValidationError,
)
from suz_sdk.signing.base import BaseSigner
from suz_sdk.signing.noop import NoopSigner

__all__ = [
    # Client
    "SuzClient",
    # Config
    "SuzConfig",
    "Environment",
    # Exceptions
    "SuzError",
    "SuzTransportError",
    "SuzTimeoutError",
    "SuzAuthError",
    "SuzTokenExpiredError",
    "SuzSignatureError",
    "SuzValidationError",
    "SuzApiError",
    "SuzRateLimitError",
    # Signing
    "BaseSigner",
    "NoopSigner",
    # Response models
    "PingResponse",
    "RegisterConnectionResponse",
    # Auth
    "TrueApiAuth",
    "TokenManager",
    "AuthApi",
    # API namespaces (for type hints)
    "IntegrationApi",
]

__version__ = "0.2.0"
