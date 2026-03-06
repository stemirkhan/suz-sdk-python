"""Public ``client.auth`` interface for the SUZ SDK.

Exposes high-level authentication operations to SDK users.
"""

from suz_sdk.auth.token_manager import TokenManager
from suz_sdk.exceptions import SuzError


class AuthApi:
    """Public authentication interface, accessible via ``client.auth``.

    Wraps a :class:`TokenManager` and exposes the operations that SDK users
    care about.  The manager handles TTL tracking, thread safety, and
    pre-refresh internally.

    Args:
        token_manager: Configured TokenManager, or None if automatic token
                       management is not set up (e.g., when a static
                       ``client_token`` is used instead).
    """

    def __init__(self, token_manager: TokenManager | None) -> None:
        self._token_manager = token_manager

    def authenticate(self) -> str:
        """Force a token refresh and return the new clientToken.

        Call this once at startup to obtain the first token, or to recover
        after receiving an HTTP 401.

        Returns:
            Newly obtained clientToken string.

        Raises:
            SuzError:          No auth method is configured (no signer +
                               oms_connection provided to SuzClient).
            SuzAuthError:      Authentication failed.
            SuzTransportError: Network failure during authentication.
        """
        if self._token_manager is None:
            raise SuzError(
                "Automatic token management is not configured. "
                "Provide `signer` and `oms_connection` to SuzClient, "
                "or pass `client_token` directly."
            )
        return self._token_manager.authenticate()
