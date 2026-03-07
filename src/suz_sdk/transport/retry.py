"""RetryConfig — configuration for automatic HTTP request retries in the SUZ SDK."""

from dataclasses import dataclass, field


@dataclass
class RetryConfig:
    """Configuration for automatic HTTP request retries.

    Passed to ``HttpxTransport`` or ``AsyncHttpxTransport`` to enable retry
    behaviour.  By default, retries happen on 5xx responses and network-level
    failures with exponential backoff.

    Backoff formula::

        wait = backoff_factor * 2 ** attempt   (seconds)

    With defaults: 0.5 s → 1.0 s → 2.0 s for three retries.

    Args:
        max_retries:             Maximum number of retry attempts after the
                                 first failure.  0 = no retries.
        backoff_factor:          Multiplier for exponential backoff.
                                 Default: 0.5.
        retry_statuses:          HTTP status codes that trigger a retry.
                                 Default: {500, 502, 503, 504}.
        retry_on_network_errors: Whether to retry on ``SuzTimeoutError`` and
                                 ``SuzTransportError``.  Default: True.
    """

    max_retries: int = 3
    backoff_factor: float = 0.5
    retry_statuses: frozenset[int] = field(
        default_factory=lambda: frozenset({500, 502, 503, 504})
    )
    retry_on_network_errors: bool = True
