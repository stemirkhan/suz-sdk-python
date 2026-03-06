"""Configuration for the SUZ SDK.

SuzConfig is the single source of truth for all SDK settings.
It is built once, validated by Pydantic v2, and passed to SuzClient.

Environment notes (§9.2.1 of the API PDF):
    The PDF specifies two base URLs for the registration endpoint:
        Sandbox:    https://suz-integrator.sandbox.crptech.ru
        Production: https://suzgrid.crpt.ru:16443

    IMPORTANT: The main API URL (for ping, orders, reports, etc.) is
    instance-specific — the PDF refers to it as "<url стенда>" without
    giving a universal address.  Users MUST supply their own base_url
    when constructing SuzClient.

    TODO(api-urls): Clarify whether sandbox/production have fixed base URLs
    for the main API (ping, orders) or if they are always OMS-instance-specific.
    Update Environment defaults once confirmed.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from suz_sdk.signing.base import BaseSigner


class Environment(str, Enum):
    """Predefined environments for the СУЗ API.

    Choose SANDBOX for development and testing.  Use PRODUCTION for
    live integrations.

    The sandbox registration key (§9.2.1):
        4344d884-7f21-456c-981e-cd68e92391e8
    """

    SANDBOX = "sandbox"
    PRODUCTION = "production"


# Known base URLs confirmed from the API PDF (§9.2.1).
# These are used as defaults when base_url is not explicitly provided.
# NOTE: The PDF specifies these as registration-endpoint URLs.  The main API
# URL (for ping, orders) may differ — verify with your СУЗ instance operator.
_ENVIRONMENT_BASE_URLS: dict[Environment, str] = {
    Environment.SANDBOX: "https://suz-integrator.sandbox.crptech.ru",
    Environment.PRODUCTION: "https://suzgrid.crpt.ru:16443",
}


class SuzConfig(BaseModel):
    """Configuration for SuzClient.

    Attributes:
        oms_id:           UUID of the СУЗ instance.  Required.  Passed as
                          `omsId` query parameter on every API request.
        environment:      Predefined environment (SANDBOX or PRODUCTION).
                          Used to set a default base_url if none is given.
        base_url:         Explicit base URL override.  Takes priority over
                          environment default.  Must not have a trailing slash.
        signer:           Signing implementation.  Required for endpoints that
                          mandate X-Signature (registration, some reports).
                          Optional for read-only calls like ping.
        client_token:     A pre-obtained clientToken to inject into requests.
                          In later iterations this will be managed automatically
                          by TokenManager.
        oms_connection:   UUID of the registered integration installation
                          (omsConnection).  Required for token operations.
        registration_key: Registration key issued by CRPT.
                          Sandbox key: 4344d884-7f21-456c-981e-cd68e92391e8
        timeout:          HTTP request timeout in seconds.  Default: 30.
        verify_ssl:       Whether to verify TLS certificates.  Default: True.
        user_agent:       Value for the User-Agent HTTP header.
    """

    model_config = {"arbitrary_types_allowed": True}

    oms_id: str = Field(..., description="UUID of the СУЗ instance (omsId)")
    environment: Environment = Field(
        default=Environment.SANDBOX, description="Target environment"
    )
    base_url: str | None = Field(
        default=None,
        description=(
            "Explicit base URL.  If not set, derived from `environment`. "
            "Must not have a trailing slash."
        ),
    )
    signer: BaseSigner | None = Field(
        default=None,
        description="Signer for X-Signature header.  Required for signed endpoints.",
    )
    client_token: str | None = Field(
        default=None,
        description="Pre-obtained clientToken.  Managed by TokenManager in later iterations.",
    )
    oms_connection: str | None = Field(
        default=None,
        description="UUID of the registered integration installation (omsConnection).",
    )
    registration_key: str | None = Field(
        default=None,
        description="Registration key for integration installation.",
    )
    timeout: float = Field(default=30.0, gt=0, description="HTTP timeout in seconds.")
    verify_ssl: bool = Field(default=True, description="Verify TLS certificates.")
    user_agent: str = Field(
        default="suz-sdk-python/0.1.0",
        description="User-Agent header value.",
    )

    @model_validator(mode="before")
    @classmethod
    def _strip_base_url_slash(cls, data: Any) -> Any:
        """Strip trailing slashes from base_url before validation."""
        if isinstance(data, dict) and isinstance(data.get("base_url"), str):
            data["base_url"] = data["base_url"].rstrip("/")
        return data

    def resolved_base_url(self) -> str:
        """Return the effective base URL (explicit or derived from environment).

        Returns:
            Base URL string without trailing slash.
        """
        if self.base_url:
            return self.base_url
        return _ENVIRONMENT_BASE_URLS[self.environment]
