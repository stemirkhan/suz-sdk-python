# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.9.0] — 2026-03-07

### Changed

- `Environment` now inherits from `StrEnum` instead of `str, Enum` (Python 3.11+)

### Fixed

- **mypy strict**: removed 10 now-unnecessary `# type: ignore` comments that mypy 1.9 no longer requires; `resp.body` assignment to typed variables is now accepted without annotation suppression
- **mypy strict**: `get_product_info()` in `OrdersApi` / `AsyncOrdersApi` now uses `cast(dict[str, dict[str, Any]], resp.body)` to satisfy `no-any-return`
- **mypy strict**: `get_receipt()` in `ReportsApi` / `AsyncReportsApi` now uses `cast(list[dict[str, Any]], ...)` for the same reason
- **ruff**: import blocks re-sorted in `__init__.py`, `orders.py`, `async_orders.py`, `reports.py`, `async_reports.py`; `Callable` moved from `typing` to `collections.abc`; `datetime.UTC` alias applied; unused imports removed (`ConnectionInfo` in `async_integration.py`, `field` in `reports.py`)
- `_parse_buffer_info` uses `.get()` with safe defaults for fields that may be absent in `list_orders` responses (`availableCodes`, `totalPassed`, `poolsExhausted`, `templateId`)

---

## [0.8.0] — 2026-03-07

### Added

- **Orders — 5 new methods** (sync + async):
  - `list_orders()` — `GET /api/v3/order/list` — all orders for the OMS instance (§4.4.3)
  - `get_blocks()` — `GET /api/v3/order/codes/blocks` — delivered code blocks for order + GTIN (§4.4.5)
  - `get_codes_retry()` — `GET /api/v3/order/codes/retry` — re-fetch a block by `blockId` after network loss (§4.4.6)
  - `get_product_info()` — `GET /api/v3/order/product` — free-form product attributes keyed by GTIN (§4.4.7)
  - `search_orders()` — `POST /api/v3/orders/search` — paginated search with `OrderFilter` (§4.4.29)
- **Integration — 2 new methods** (sync + async):
  - `list_connections()` — `GET /api/v3/integration/connection` — paginated list of registered connections (§4.4.26)
  - `delete_connection()` — `DELETE /api/v3/integration/connection` — remove a connection by UUID (§4.4.27)
- New models: `Block`, `GetBlocksResponse`, `OrderSummaryInfo`, `ListOrdersResponse`, `OrderFilter`, `SearchOrdersResponse`, `ConnectionInfo`, `ListConnectionsResponse`, `DeleteConnectionResponse` — all exported from the top-level `suz_sdk` package
- `IntegrationApi` and `AsyncIntegrationApi` accept optional `get_auth_headers` for authenticated endpoints
- 67 new tests (46 sync + 21 async); total: 327 tests, all passing

---

## [0.7.0] — 2026-03-07

### Added

- `RetryConfig` — dataclass for configuring automatic HTTP retries: `max_retries` (default 3), `backoff_factor` (default 0.5 s), `retry_statuses` (default `{500, 502, 503, 504}`), `retry_on_network_errors` (default `True`)
- Both `HttpxTransport` and `AsyncHttpxTransport` accept an optional `retry: RetryConfig` parameter; retries use exponential backoff (`backoff_factor * 2^attempt`) with `WARNING`-level log on each retry
- `RetryConfig` exported from the top-level `suz_sdk` package
- `py.typed` marker file — package is now PEP 561 compliant; mypy/pyright can verify consumer code against the SDK's type annotations
- `anyio[asyncio]` and `pytest-anyio` added to dev dependencies
- Upgraded token-refresh log level from `DEBUG` to `INFO` in `TokenManager` and `AsyncTokenManager`
- 24 new tests covering `RetryConfig` defaults, 5xx retry, network-error retry, backoff timing, no-retry on 4xx, async retry; total: 260 tests, all passing

---

## [0.6.0] — 2026-03-07

### Added

- `AsyncSuzClient` — async counterpart to `SuzClient`, built on `httpx.AsyncClient`; supports `async with` context manager and `await client.aclose()`
- `AsyncHttpxTransport` — async HTTP transport wrapping `httpx.AsyncClient`; identical error mapping to the sync transport
- `AsyncHealthApi`, `AsyncIntegrationApi`, `AsyncOrdersApi`, `AsyncReportsApi` — async API modules mirroring the sync API surface
- `AsyncTrueApiAuth` — async implementation of the two-step True API auth flow (GET `/auth/key` → POST `/auth/simpleSignIn/{omsConnection}`)
- `AsyncTokenManager` — async token cache with `asyncio.Lock` for concurrency-safe refresh; `get_token()` and `authenticate()` coroutines
- `AsyncAuthApi` — exposes `await client.auth.authenticate()` on `AsyncSuzClient`
- All new classes exported from the top-level `suz_sdk` package
- 34 new unit tests with `@pytest.mark.anyio` covering structure, context manager, auth headers, all API methods, auth flow, and exports
- Total: 236 tests, all passing

---

## [0.5.0] — 2026-03-07

### Added

- `CryptoProSigner` — production-ready signer that delegates to the CryptoPro CSP `cryptcp` CLI tool; produces detached DER-encoded CMS signatures (GOST R 34.10-2012) Base64-encoded, as required by the X-Signature header (§2.3.1)
- Constructor options: `thumbprint` (SHA-1 hex, 40 chars), `cryptcp_path` (default `"cryptcp"`, override to `/opt/cprocsp/bin/amd64/cryptcp` on Linux), `nochain`, `nopolicy`, `extra_args`, `timeout`
- `SuzSigningError` — new client-side exception raised when local signing fails (cryptcp not found, non-zero exit, timeout); distinct from `SuzSignatureError` which is the server-side HTTP 413
- Both `CryptoProSigner` and `SuzSigningError` exported from the top-level `suz_sdk` package
- 30 new unit tests covering happy path, command construction (all flags), error handling (FileNotFoundError, non-zero exit, timeout, missing output file), and protocol conformance
- `pyproject.toml` version corrected and aligned with package version

---

## [0.4.0] — 2026-03-07

### Added

- `client.reports.send_utilisation()` — sends a KM utilisation (marking) report (`POST /api/v3/utilisation?omsId=…`); signs request body with `X-Signature` when a signer is configured; supports `utilisation_type` (UTILISATION / RESORT / SPLITMARK / DIVISIONMARK) and product-group-specific `attributes`; returns `SendUtilisationResponse` with `oms_id` and `report_id`
- `client.reports.get_report_status()` — polls report processing status (`GET /api/v3/report/info`); returns `ReportStatusResponse` with `report_status` (SUCCESS / REJECTED / …) and optional `error_reason`
- `client.reports.get_receipt()` — retrieves receipts by document ID (`GET /api/v3/receipts/receipt`); works with Квитирование 2.0 receipts for orders, reports, and KM blocks; returns raw list of receipt dicts
- `client.reports.search_receipts()` — searches receipts by filters (`POST /api/v3/receipts/receipt/search`); supports date ranges, resultDocIds, orderIds, workflowTypes, productGroups, and more; pagination via `limit` / `skip`; returns `SearchReceiptsResponse` with `total_count` and `results`
- `ReportsApi` class and models (`SendUtilisationResponse`, `ReportStatusResponse`, `ReceiptFilter`, `SearchReceiptsResponse`) exported from the top-level `suz_sdk` package
- `SuzClient.reports` attribute — wired automatically with the main transport, auth headers, and signer
- 45 new unit tests covering all four report methods, request structure, signing, filter serialisation, optional parameters, and client wiring

---

## [0.3.0] — 2026-03-06

### Added

- `client.orders.create()` — creates a KM emission order (`POST /api/v3/order?omsId=…`); signs request body with `X-Signature` when a signer is configured; returns `CreateOrderResponse` with `order_id` and `expected_complete_timestamp`
- `client.orders.get_status()` — polls buffer status for an order (`GET /api/v3/order/status`); returns a list of `BufferInfo` objects with `buffer_status` (ACTIVE / PENDING / REJECTED), `available_codes`, `rejection_reason`, etc.
- `client.orders.get_codes()` — fetches a block of KM codes from an active order (`GET /api/v3/codes`); returns `GetCodesResponse` with `codes` list and `block_id`
- `client.orders.close()` — closes an order or individual sub-order by GTIN (`POST /api/v3/order/close`); signs request body when signer is configured; returns `CloseOrderResponse`
- `OrdersApi` class and models (`OrderProduct`, `CreateOrderResponse`, `BufferInfo`, `GetCodesResponse`, `CloseOrderResponse`) exported from the top-level `suz_sdk` package
- `SuzClient.orders` attribute — wired automatically with the main transport, auth headers, and signer
- 36 new unit tests covering all four orders methods, request structure, signing, error propagation, and client wiring

---

## [0.2.0] — 2026-03-06

### Added

- `client.integration.register_connection()` — registers an integration installation with СУЗ (`POST /api/v3/integration/connection`); signs the request body with `X-Signature`, passes `X-RegistrationKey`; returns `RegisterConnectionResponse` with `status`, `omsConnection`, `name`, `rejectionReason`
- `TrueApiAuth` — two-step True API (GIS MT) authentication flow (§9.3.2): `GET /auth/key` → sign challenge → `POST /auth/simpleSignIn/{omsConnection}` → clientToken
- `TokenManager` — thread-safe in-memory token cache with 10-hour TTL, 5-minute pre-refresh, and serialized renewal (re-issuing invalidates the previous token)
- `AuthApi` — public `client.auth` interface exposing `authenticate()` for explicit token refresh
- `SuzClient.auth` and `SuzClient.integration` sub-module attributes
- `SuzConfig.true_api_url` — explicit override for the True API base URL; defaults per environment (sandbox: `markirovka.sandbox.crptech.ru`, production: `markirovka.crpt.ru`)
- `Request.raw_body` field in the transport layer — allows API modules to pre-serialize bodies for signing and send bytes verbatim
- 40 new unit tests covering integration registration, True API auth flow, TokenManager TTL logic, and thread-safety
- Auto token management: when both `signer` and `oms_connection` are provided to `SuzClient`, `_auth_headers()` automatically calls `TokenManager.get_token()` with transparent pre-refresh

### Changed

- `SuzClient` now accepts `true_api_url` constructor argument
- `SuzConfig` docstring updated to document `true_api_url` and updated `client_token` semantics
- `__version__` bumped to `0.2.0`

---

## [0.1.0] — 2026-03-06

### Added

- `SuzClient` — main entry point with context manager support
- `SuzConfig` + `Environment` — Pydantic v2 configuration model with SANDBOX/PRODUCTION presets
- Typed exception hierarchy: `SuzError`, `SuzTransportError`, `SuzTimeoutError`, `SuzAuthError`, `SuzTokenExpiredError`, `SuzSignatureError`, `SuzValidationError`, `SuzApiError`, `SuzRateLimitError`
- `BaseSigner` Protocol — pluggable signing abstraction for `X-Signature` header
- `NoopSigner` — no-op implementation for tests and development
- `HttpxTransport` — synchronous HTTP transport backed by `httpx` with full error mapping
- `BaseTransport` Protocol + `Request`/`Response` dataclasses for transport-layer abstraction
- `client.health.ping()` — availability and version check (`GET /api/v3/ping`)
- `PingResponse` — typed Pydantic model for ping response
- 51 unit tests covering config, exceptions, signing, transport, and health API
- English and Russian documentation (`README.md`, `README.ru.md`)
- `CONTRIBUTING.md` — contribution guide

[Unreleased]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/stemirkhan/suz-sdk-python/releases/tag/v0.1.0
