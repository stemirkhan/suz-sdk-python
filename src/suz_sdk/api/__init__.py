"""High-level API endpoint clients for the SUZ SDK.

Each module in this package wraps one group of related SUZ API endpoints
and presents a clean, typed Python interface.  All HTTP mechanics live
in the transport layer — the API modules only deal with request construction
and response parsing.

Implemented in this iteration:
    health  — ping / availability check (§4.4.25)

Planned for future iterations:
    integration — register_connection (§9.2.1)
    orders      — create, get_status, get_codes, close
    reports     — send_utilisation, get_status
    receipts    — get
"""

from suz_sdk.api.health import HealthApi, PingResponse

__all__ = ["HealthApi", "PingResponse"]
