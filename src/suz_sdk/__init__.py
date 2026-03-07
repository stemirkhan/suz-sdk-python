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
from suz_sdk.api.orders import (
    BufferInfo,
    CloseOrderResponse,
    CreateOrderResponse,
    GetCodesResponse,
    OrderProduct,
    OrdersApi,
)
from suz_sdk.api.reports import (
    ReceiptFilter,
    ReportStatusResponse,
    ReportsApi,
    SearchReceiptsResponse,
    SendUtilisationResponse,
)
from suz_sdk.api.async_health import AsyncHealthApi
from suz_sdk.api.async_integration import AsyncIntegrationApi
from suz_sdk.api.async_orders import AsyncOrdersApi
from suz_sdk.api.async_reports import AsyncReportsApi
from suz_sdk.async_client import AsyncSuzClient
from suz_sdk.auth.async_auth_api import AsyncAuthApi
from suz_sdk.auth.async_token_manager import AsyncTokenManager
from suz_sdk.auth.async_true_api import AsyncTrueApiAuth
from suz_sdk.auth.auth_api import AuthApi
from suz_sdk.auth.token_manager import TokenManager
from suz_sdk.auth.true_api import TrueApiAuth
from suz_sdk.client import SuzClient
from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport
from suz_sdk.config import Environment, SuzConfig
from suz_sdk.exceptions import (
    SuzApiError,
    SuzAuthError,
    SuzError,
    SuzRateLimitError,
    SuzSignatureError,
    SuzSigningError,
    SuzTimeoutError,
    SuzTokenExpiredError,
    SuzTransportError,
    SuzValidationError,
)
from suz_sdk.signing.base import BaseSigner
from suz_sdk.signing.cryptopro import CryptoProSigner
from suz_sdk.signing.noop import NoopSigner

__all__ = [
    # Clients
    "SuzClient",
    "AsyncSuzClient",
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
    "SuzSigningError",
    "SuzValidationError",
    "SuzApiError",
    "SuzRateLimitError",
    # Signing
    "BaseSigner",
    "NoopSigner",
    "CryptoProSigner",
    # Response models
    "PingResponse",
    "RegisterConnectionResponse",
    "CreateOrderResponse",
    "BufferInfo",
    "GetCodesResponse",
    "CloseOrderResponse",
    # Request models
    "OrderProduct",
    # Response models (reports)
    "SendUtilisationResponse",
    "ReportStatusResponse",
    "SearchReceiptsResponse",
    # Request models (reports)
    "ReceiptFilter",
    # Sync API namespaces
    "OrdersApi",
    "ReportsApi",
    "IntegrationApi",
    # Sync auth
    "TrueApiAuth",
    "TokenManager",
    "AuthApi",
    # Async API namespaces
    "AsyncHealthApi",
    "AsyncIntegrationApi",
    "AsyncOrdersApi",
    "AsyncReportsApi",
    # Async auth
    "AsyncTrueApiAuth",
    "AsyncTokenManager",
    "AsyncAuthApi",
    # Async transport
    "AsyncHttpxTransport",
]

__version__ = "0.6.0"
