"""Tests for TokenManager (§4.3 of technical spec).

TokenManager is tested with a mock TrueApiAuth to avoid network calls.
"""

import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from suz_sdk.auth.token_manager import TokenManager, _PRE_REFRESH_SECONDS, _TRUE_API_TOKEN_TTL_HOURS
from suz_sdk.exceptions import SuzAuthError


def _make_manager(token: str = "tok-1") -> tuple[TokenManager, MagicMock]:
    """Create a TokenManager backed by a mock TrueApiAuth."""
    mock_auth = MagicMock()
    mock_auth.fetch_token.return_value = token
    manager = TokenManager(auth=mock_auth)
    return manager, mock_auth


class TestGetToken:
    def test_fetches_token_on_first_call(self) -> None:
        manager, mock_auth = _make_manager("tok-abc")
        token = manager.get_token()
        assert token == "tok-abc"
        mock_auth.fetch_token.assert_called_once()

    def test_reuses_cached_token_on_subsequent_calls(self) -> None:
        manager, mock_auth = _make_manager("tok-1")
        manager.get_token()
        manager.get_token()
        assert mock_auth.fetch_token.call_count == 1

    def test_refreshes_when_token_is_none(self) -> None:
        manager, mock_auth = _make_manager("new-tok")
        manager._token = None
        manager._expires_at = None
        token = manager.get_token()
        assert token == "new-tok"
        mock_auth.fetch_token.assert_called_once()

    def test_refreshes_when_expires_at_is_none(self) -> None:
        manager, mock_auth = _make_manager("new-tok")
        manager._token = "old-tok"
        manager._expires_at = None
        token = manager.get_token()
        assert token == "new-tok"

    def test_refreshes_when_token_near_expiry(self) -> None:
        manager, mock_auth = _make_manager("fresh-tok")
        manager._token = "stale-tok"
        # Set expires_at just inside the pre-refresh window.
        manager._expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=_PRE_REFRESH_SECONDS - 10
        )
        token = manager.get_token()
        assert token == "fresh-tok"
        mock_auth.fetch_token.assert_called_once()

    def test_does_not_refresh_when_token_has_plenty_of_time(self) -> None:
        manager, mock_auth = _make_manager("new-tok")
        manager._token = "good-tok"
        manager._expires_at = datetime.now(timezone.utc) + timedelta(hours=5)
        token = manager.get_token()
        assert token == "good-tok"
        mock_auth.fetch_token.assert_not_called()

    def test_sets_expiry_after_refresh(self) -> None:
        manager, _ = _make_manager()
        before = datetime.now(timezone.utc)
        manager.get_token()
        after = datetime.now(timezone.utc)

        expected_ttl = timedelta(hours=_TRUE_API_TOKEN_TTL_HOURS)
        assert manager._expires_at is not None
        assert before + expected_ttl <= manager._expires_at <= after + expected_ttl

    def test_propagates_auth_error_from_fetch(self) -> None:
        mock_auth = MagicMock()
        mock_auth.fetch_token.side_effect = SuzAuthError("auth failed")
        manager = TokenManager(auth=mock_auth)
        with pytest.raises(SuzAuthError):
            manager.get_token()


class TestAuthenticate:
    def test_forces_refresh_and_returns_new_token(self) -> None:
        manager, mock_auth = _make_manager("tok-1")
        mock_auth.fetch_token.side_effect = ["tok-1", "tok-2"]
        manager.get_token()  # first fetch
        token = manager.authenticate()  # forced refresh
        assert token == "tok-2"
        assert mock_auth.fetch_token.call_count == 2

    def test_authenticate_on_fresh_manager_fetches_token(self) -> None:
        manager, mock_auth = _make_manager("tok-fresh")
        token = manager.authenticate()
        assert token == "tok-fresh"
        mock_auth.fetch_token.assert_called_once()


class TestThreadSafety:
    def test_concurrent_get_token_calls_fetch_once(self) -> None:
        """Under concurrent access, fetch_token should be called exactly once."""
        call_count = 0
        lock = threading.Lock()

        def slow_fetch() -> str:
            nonlocal call_count
            # Simulate I/O delay so threads pile up.
            import time
            time.sleep(0.05)
            with lock:
                call_count += 1
            return "shared-tok"

        mock_auth = MagicMock()
        mock_auth.fetch_token.side_effect = slow_fetch
        manager = TokenManager(auth=mock_auth)

        results: list[str] = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                results.append(manager.get_token())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert all(r == "shared-tok" for r in results)
        # The lock ensures only one refresh; subsequent calls reuse the cache.
        assert mock_auth.fetch_token.call_count == 1
