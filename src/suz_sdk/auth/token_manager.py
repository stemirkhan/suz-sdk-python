"""Thread-safe token manager for the SUZ SDK (§4.3 of technical spec).

Manages a single clientToken in memory with:
    - Automatic refresh when the token is missing or near expiry.
    - Pre-refresh to avoid requests failing due to a stale token.
    - Thread-safe renewal via a lock: re-issuing a token invalidates the
      previous one (§9.2 footnote), so only one thread must refresh at a time.

Token TTL (§9.3.2, Table 380):
    True API tokens are valid for 10 hours.  The manager tracks the expiry
    time and pre-refreshes 5 minutes before expiration.
"""

import logging
import threading
from datetime import datetime, timedelta, timezone

from suz_sdk.auth.true_api import TrueApiAuth

logger = logging.getLogger(__name__)

# Pre-refresh the token this many seconds before it expires.
_PRE_REFRESH_SECONDS = 300  # 5 minutes

# True API token TTL per §9.3.2, Table 380.
_TRUE_API_TOKEN_TTL_HOURS = 10


class TokenManager:
    """In-memory, thread-safe token cache for a single omsConnection.

    Usage:
        # Obtain the current token (refreshes automatically if needed).
        token = manager.get_token()

        # Force an immediate refresh (e.g., after receiving HTTP 401).
        token = manager.authenticate()

    Args:
        auth: TrueApiAuth instance used to fetch a fresh token.

    Thread safety:
        All state mutations are protected by ``_lock``.  Because re-issuing a
        token invalidates the previous one, only one concurrent refresh is
        allowed.  Other threads block until the refresh completes and then
        reuse the newly obtained token.
    """

    def __init__(self, auth: TrueApiAuth) -> None:
        self._auth = auth
        self._token: str | None = None
        self._expires_at: datetime | None = None
        self._lock = threading.Lock()

    def get_token(self) -> str:
        """Return the current token, refreshing it if necessary.

        If the token is absent or will expire within ``_PRE_REFRESH_SECONDS``,
        a fresh token is fetched before returning.

        Returns:
            Current valid clientToken string.

        Raises:
            SuzAuthError:      Authentication failed.
            SuzTransportError: Network-level failure during refresh.
        """
        with self._lock:
            if self._needs_refresh():
                self._do_refresh()
            # _do_refresh always sets _token to a non-None value or raises.
            return self._token  # type: ignore[return-value]

    def authenticate(self) -> str:
        """Force an immediate token refresh regardless of TTL.

        Use this to recover from an HTTP 401 or to explicitly re-authenticate.

        Returns:
            Newly obtained clientToken string.

        Raises:
            SuzAuthError:      Authentication failed.
            SuzTransportError: Network-level failure during refresh.
        """
        with self._lock:
            self._do_refresh()
            return self._token  # type: ignore[return-value]

    def _needs_refresh(self) -> bool:
        """Return True if the token is absent or expires soon."""
        if self._token is None or self._expires_at is None:
            return True
        remaining = (self._expires_at - datetime.now(timezone.utc)).total_seconds()
        return remaining < _PRE_REFRESH_SECONDS

    def _do_refresh(self) -> None:
        """Fetch a new token and update internal state.

        Must be called with ``_lock`` held.
        """
        logger.debug("Refreshing clientToken via True API")
        self._token = self._auth.fetch_token()
        self._expires_at = datetime.now(timezone.utc) + timedelta(
            hours=_TRUE_API_TOKEN_TTL_HOURS
        )
        logger.debug("clientToken refreshed; expires at %s", self._expires_at.isoformat())
