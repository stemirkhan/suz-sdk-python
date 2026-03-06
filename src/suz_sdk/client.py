"""SuzClient — public entry point for the SUZ SDK.

Usage:
    from suz_sdk import SuzClient, Environment

    client = SuzClient(
        oms_id="cdf12109-10d3-11e6-8b6f-0050569977a1",
        environment=Environment.SANDBOX,
        client_token="1cecc8fb-fb47-4c8a-af3d-d34c1ead8c4f",
    )

    info = client.health.ping()
    print(info.oms_version)

Design notes:
    - SuzClient owns all sub-clients (health, …) and wires them together.
    - It provides a single ``_auth_headers()`` method so all API sub-modules
      share the same token injection logic.  When TokenManager is added in
      Iteration 2, only this method changes.
    - The underlying transport is created internally but can be inspected or
      replaced by passing a custom ``transport`` argument (useful in tests).
    - SuzClient implements the context manager protocol so it can be used in
      a ``with`` block to ensure the transport's connection pool is closed.
"""

from typing import Any

from suz_sdk.api.health import HealthApi
from suz_sdk.config import Environment, SuzConfig
from suz_sdk.signing.base import BaseSigner
from suz_sdk.transport.base import BaseTransport
from suz_sdk.transport.httpx_transport import HttpxTransport


class SuzClient:
    """Synchronous client for the СУЗ API 3.0.

    All API sub-modules are accessible as attributes:
        client.health   → HealthApi

    Args:
        oms_id:           Required.  UUID of the СУЗ instance (omsId).
        environment:      SANDBOX or PRODUCTION.  Used to derive base_url
                          if not explicitly set.  Default: SANDBOX.
        base_url:         Explicit base URL override.  Overrides environment
                          default.
        client_token:     Pre-obtained clientToken.  Injected into every
                          request that requires authorization.
                          TODO(iter2): Replace with TokenManager auto-refresh.
        signer:           Signing implementation for X-Signature header.
                          Required for endpoints that mandate a signature.
        oms_connection:   UUID of the registered integration installation.
        registration_key: Registration key for the integration installation.
        timeout:          HTTP timeout in seconds.  Default: 30.
        verify_ssl:       TLS certificate verification.  Default: True.
        transport:        Optional custom transport.  If provided, all other
                          transport-related arguments are ignored.  Useful for
                          injecting test doubles.
    """

    def __init__(
        self,
        oms_id: str,
        environment: Environment = Environment.SANDBOX,
        base_url: str | None = None,
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
            client_token=client_token,
            signer=signer,
            oms_connection=oms_connection,
            registration_key=registration_key,
            timeout=timeout,
            verify_ssl=verify_ssl,
        )

        # Allow injecting a custom transport (e.g., a test double).
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

        # Wire up API sub-modules.
        self.health = HealthApi(
            transport=self._transport,
            oms_id=self._config.oms_id,
            get_auth_headers=self._auth_headers,
        )

    # ------------------------------------------------------------------
    # Auth header building
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        """Build authorization headers for an outgoing request.

        Currently returns the statically configured clientToken.

        TODO(iter2): Replace with TokenManager that handles auto-refresh,
        TTL tracking, and thread-safe token renewal.  A re-issued token
        invalidates the previous one (§9.1), so renewal must be serialized.

        Returns:
            Dict with 'clientToken' key if a token is configured,
            otherwise an empty dict.
        """
        headers: dict[str, str] = {}
        if self._config.client_token:
            headers["clientToken"] = self._config.client_token
        return headers

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying transport and release resources."""
        if self._owns_transport and hasattr(self._transport, "close"):
            self._transport.close()  # type: ignore[union-attr]

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
