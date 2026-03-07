"""AsyncSuzClient — async entry point for the SUZ SDK.

Usage:
    from suz_sdk import AsyncSuzClient, Environment

    # Option A: manual token (no auto-refresh)
    async with AsyncSuzClient(
        oms_id="...",
        client_token="your-token",
    ) as client:
        info = await client.health.ping()

    # Option B: auto token management via True API
    async with AsyncSuzClient(
        oms_id="...",
        oms_connection="...",
        signer=MyCryptoProSigner(),
    ) as client:
        await client.auth.authenticate()
        order = await client.orders.create(...)
"""

from typing import Any

from suz_sdk.api.async_health import AsyncHealthApi
from suz_sdk.api.async_integration import AsyncIntegrationApi
from suz_sdk.api.async_orders import AsyncOrdersApi
from suz_sdk.api.async_reports import AsyncReportsApi
from suz_sdk.auth.async_auth_api import AsyncAuthApi
from suz_sdk.auth.async_token_manager import AsyncTokenManager
from suz_sdk.auth.async_true_api import AsyncTrueApiAuth
from suz_sdk.config import Environment, SuzConfig
from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.async_httpx_transport import AsyncHttpxTransport


class AsyncSuzClient:
    """Async client for the СУЗ API 3.0.

    All API sub-modules are accessible as attributes:
        client.health        → AsyncHealthApi
        client.integration   → AsyncIntegrationApi
        client.orders        → AsyncOrdersApi
        client.reports       → AsyncReportsApi
        client.auth          → AsyncAuthApi

    Mirrors SuzClient but every API call is a coroutine — use with ``await``.

    Args:
        oms_id:           Required.  UUID of the СУЗ instance (omsId).
        environment:      SANDBOX or PRODUCTION.  Default: SANDBOX.
        base_url:         Explicit base URL override for the main SUZ API.
        true_api_url:     Explicit True API base URL override.
        client_token:     Pre-obtained clientToken (static, no auto-refresh).
        signer:           Signing implementation for X-Signature and True API
                          challenge.  Required for auto token management.
        oms_connection:   UUID of the registered integration installation.
                          Required for auto token management.
        registration_key: Registration key from CRPT.
        timeout:          HTTP timeout in seconds.  Default: 30.
        verify_ssl:       TLS certificate verification.  Default: True.
        transport:        Optional custom async transport (for tests).
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
        transport: AsyncHttpxTransport | None = None,
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

        if transport is not None:
            self._transport = transport
            self._owns_transport = False
        else:
            self._transport = AsyncHttpxTransport(
                base_url=self._config.resolved_base_url(),
                timeout=self._config.timeout,
                verify_ssl=self._config.verify_ssl,
                user_agent=self._config.user_agent,
            )
            self._owns_transport = True

        self._true_api_transport: AsyncHttpxTransport | None = None
        self._token_manager: AsyncTokenManager | None = None

        if self._config.signer is not None and self._config.oms_connection is not None:
            self._true_api_transport = AsyncHttpxTransport(
                base_url=self._config.resolved_true_api_url(),
                timeout=self._config.timeout,
                verify_ssl=self._config.verify_ssl,
                user_agent=self._config.user_agent,
            )
            true_api_auth = AsyncTrueApiAuth(
                oms_connection=self._config.oms_connection,
                signer=self._config.signer,
                transport=self._true_api_transport,
            )
            self._token_manager = AsyncTokenManager(auth=true_api_auth)

        self.health = AsyncHealthApi(
            transport=self._transport,
            oms_id=self._config.oms_id,
            get_auth_headers=self._auth_headers,
        )
        self.integration = AsyncIntegrationApi(
            transport=self._transport,
            oms_id=self._config.oms_id,
            signer=self._config.signer,
            registration_key=self._config.registration_key,
        )
        self.orders = AsyncOrdersApi(
            transport=self._transport,
            oms_id=self._config.oms_id,
            get_auth_headers=self._auth_headers,
            signer=self._config.signer,
        )
        self.reports = AsyncReportsApi(
            transport=self._transport,
            oms_id=self._config.oms_id,
            get_auth_headers=self._auth_headers,
            signer=self._config.signer,
        )
        self.auth = AsyncAuthApi(token_manager=self._token_manager)

    # ------------------------------------------------------------------
    # Auth header building
    # ------------------------------------------------------------------

    async def _auth_headers(self) -> dict[str, str]:
        """Build authorization headers for an outgoing request."""
        if self._token_manager is not None:
            return {"clientToken": await self._token_manager.get_token()}
        if self._config.client_token:
            return {"clientToken": self._config.client_token}
        return {}

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        """Close the underlying transports and release resources."""
        if self._owns_transport:
            await self._transport.aclose()
        if self._true_api_transport is not None:
            await self._true_api_transport.aclose()

    async def __aenter__(self) -> "AsyncSuzClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AsyncSuzClient("
            f"oms_id={self._config.oms_id!r}, "
            f"environment={self._config.environment.value!r})"
        )
