"""SuzClient — public entry point for the SUZ SDK.

Usage:
    from suz_sdk import SuzClient, Environment

    # Option A: manual token (no auto-refresh)
    client = SuzClient(
        oms_id="cdf12109-10d3-11e6-8b6f-0050569977a1",
        environment=Environment.SANDBOX,
        client_token="1cecc8fb-fb47-4c8a-af3d-d34c1ead8c4f",
    )

    # Option B: auto token management via True API
    client = SuzClient(
        oms_id="...",
        environment=Environment.SANDBOX,
        oms_connection="...",
        registration_key="...",
        signer=MyCryptoProSigner(),
    )
    client.auth.authenticate()   # fetch first token

    info = client.health.ping()
    print(info.oms_version)

Design notes:
    - SuzClient owns all sub-clients (health, integration, auth) and wires them.
    - ``_auth_headers()`` is the single point of token injection.  It reads from
      TokenManager when auto-auth is configured, or falls back to the static
      ``client_token``.
    - When TokenManager is in use, ``_auth_headers()`` triggers a transparent
      pre-refresh if the token is near expiry.
    - The underlying transport is created internally but can be replaced via
      the ``transport`` argument (useful in tests).
    - SuzClient implements the context manager protocol to ensure the connection
      pool is released cleanly.
"""

from typing import Any

from suz_sdk.api.health import HealthApi
from suz_sdk.api.integration import IntegrationApi
from suz_sdk.api.orders import OrdersApi
from suz_sdk.api.reports import ReportsApi
from suz_sdk.auth.auth_api import AuthApi
from suz_sdk.auth.token_manager import TokenManager
from suz_sdk.auth.true_api import TrueApiAuth
from suz_sdk.config import Environment, SuzConfig
from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.base import BaseTransport
from suz_sdk.transport.httpx_transport import HttpxTransport


class SuzClient:
    """Synchronous client for the СУЗ API 3.0.

    All API sub-modules are accessible as attributes:
        client.health        → HealthApi
        client.integration   → IntegrationApi
        client.auth          → AuthApi

    Args:
        oms_id:           Required.  UUID of the СУЗ instance (omsId).
        environment:      SANDBOX or PRODUCTION.  Used to derive base_url and
                          true_api_url if not explicitly set.  Default: SANDBOX.
        base_url:         Explicit base URL override for the main SUZ API.
                          Overrides environment default.
        true_api_url:     Explicit True API (GIS MT) base URL override.
                          Overrides environment default.
        client_token:     Pre-obtained clientToken.  When set, used directly
                          instead of TokenManager.
        signer:           Signing implementation for X-Signature and True API
                          challenge.  Required when using auto token management
                          or signed endpoints (register_connection).
        oms_connection:   UUID of the registered integration installation.
                          Required for auto token management.
        registration_key: Registration key from CRPT.  Required for
                          register_connection().
        timeout:          HTTP timeout in seconds.  Default: 30.
        verify_ssl:       TLS certificate verification.  Default: True.
        transport:        Optional custom transport for the main SUZ API.
                          Bypasses all transport construction.  Useful for tests.
    """

    def __init__(
        self,
        oms_id: str,
        environment: Environment = Environment.SANDBOX,
        base_url: str | None = None,
        true_api_url: str | None = None,
        client_token: str | None = None,
        signer: BaseSigner | None = None,
        oms_connection: str | None = None,
        registration_key: str | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        transport: BaseTransport | None = None,
    ) -> None:
        self._config = SuzConfig(
            oms_id=oms_id,
            environment=environment,
            base_url=base_url,
            true_api_url=true_api_url,
            client_token=client_token,
            signer=signer,
            oms_connection=oms_connection,
            registration_key=registration_key,
            timeout=timeout,
            verify_ssl=verify_ssl,
        )

        # Main SUZ API transport.
        if transport is not None:
            self._transport: BaseTransport = transport
            self._owns_transport = False
        else:
            self._transport = HttpxTransport(
                base_url=self._config.resolved_base_url(),
                timeout=self._config.timeout,
                verify_ssl=self._config.verify_ssl,
                user_agent=self._config.user_agent,
            )
            self._owns_transport = True

        # True API transport + TokenManager — only when signer+oms_connection are set.
        self._true_api_transport: HttpxTransport | None = None
        self._token_manager: TokenManager | None = None

        if self._config.signer is not None and self._config.oms_connection is not None:
            self._true_api_transport = HttpxTransport(
                base_url=self._config.resolved_true_api_url(),
                timeout=self._config.timeout,
                verify_ssl=self._config.verify_ssl,
                user_agent=self._config.user_agent,
            )
            true_api_auth = TrueApiAuth(
                oms_connection=self._config.oms_connection,
                signer=self._config.signer,
                transport=self._true_api_transport,
            )
            self._token_manager = TokenManager(auth=true_api_auth)

        # Wire up public API sub-modules.
        self.health = HealthApi(
            transport=self._transport,
            oms_id=self._config.oms_id,
            get_auth_headers=self._auth_headers,
        )
        self.integration = IntegrationApi(
            transport=self._transport,
            oms_id=self._config.oms_id,
            signer=self._config.signer,
            registration_key=self._config.registration_key,
            get_auth_headers=self._auth_headers,
        )
        self.orders = OrdersApi(
            transport=self._transport,
            oms_id=self._config.oms_id,
            get_auth_headers=self._auth_headers,
            signer=self._config.signer,
        )
        self.reports = ReportsApi(
            transport=self._transport,
            oms_id=self._config.oms_id,
            get_auth_headers=self._auth_headers,
            signer=self._config.signer,
        )
        self.auth = AuthApi(token_manager=self._token_manager)

    # ------------------------------------------------------------------
    # Auth header building
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        """Build authorization headers for an outgoing request.

        Priority:
            1. TokenManager (auto-refresh, TTL tracking) — when signer +
               oms_connection are both configured.
            2. Static client_token — when provided directly.
            3. Empty dict — no auth configured.

        Returns:
            Dict with 'clientToken' key, or an empty dict.
        """
        if self._token_manager is not None:
            return {"clientToken": self._token_manager.get_token()}
        if self._config.client_token:
            return {"clientToken": self._config.client_token}
        return {}

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying transports and release resources."""
        if self._owns_transport and hasattr(self._transport, "close"):
            self._transport.close()
        if self._true_api_transport is not None:
            self._true_api_transport.close()

    def __enter__(self) -> "SuzClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"SuzClient("
            f"oms_id={self._config.oms_id!r}, "
            f"environment={self._config.environment.value!r})"
        )
