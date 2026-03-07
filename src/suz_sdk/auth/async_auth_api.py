"""Async public client.auth interface for the SUZ SDK."""

from suz_sdk.auth.async_token_manager import AsyncTokenManager
from suz_sdk.exceptions import SuzError


class AsyncAuthApi:
    """Async authentication interface, accessible via ``client.auth``.

    Args:
        token_manager: Configured AsyncTokenManager, or None when a static
                       client_token is used.
    """

    def __init__(self, token_manager: AsyncTokenManager | None) -> None:
        self._token_manager = token_manager

    async def authenticate(self) -> str:
        """Force a token refresh and return the new clientToken.

        Raises:
            SuzError: No auth method is configured.
        """
        if self._token_manager is None:
            raise SuzError(
                "Automatic token management is not configured. "
                "Provide `signer` and `oms_connection` to AsyncSuzClient, "
                "or pass `client_token` directly."
            )
        return await self._token_manager.authenticate()
