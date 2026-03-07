"""Async token manager for the SUZ SDK."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from suz_sdk.auth.async_true_api import AsyncTrueApiAuth

logger = logging.getLogger(__name__)

_PRE_REFRESH_SECONDS = 300  # 5 minutes
_TRUE_API_TOKEN_TTL_HOURS = 10


class AsyncTokenManager:
    """In-memory async token cache for a single omsConnection.

    Mirrors TokenManager but uses asyncio.Lock for coroutine-safe renewal.

    Args:
        auth: AsyncTrueApiAuth instance used to fetch a fresh token.
    """

    def __init__(self, auth: AsyncTrueApiAuth) -> None:
        self._auth = auth
        self._token: str | None = None
        self._expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        """Return the current token, refreshing it if necessary.

        Returns:
            Current valid clientToken string.
        """
        async with self._lock:
            if self._needs_refresh():
                await self._do_refresh()
            return self._token  # type: ignore[return-value]

    async def authenticate(self) -> str:
        """Force an immediate token refresh regardless of TTL.

        Returns:
            Newly obtained clientToken string.
        """
        async with self._lock:
            await self._do_refresh()
            return self._token  # type: ignore[return-value]

    def _needs_refresh(self) -> bool:
        if self._token is None or self._expires_at is None:
            return True
        remaining = (self._expires_at - datetime.now(timezone.utc)).total_seconds()
        return remaining < _PRE_REFRESH_SECONDS

    async def _do_refresh(self) -> None:
        logger.debug("Refreshing clientToken via True API (async)")
        self._token = await self._auth.fetch_token()
        self._expires_at = datetime.now(timezone.utc) + timedelta(
            hours=_TRUE_API_TOKEN_TTL_HOURS
        )
        logger.debug("clientToken refreshed; expires at %s", self._expires_at.isoformat())
