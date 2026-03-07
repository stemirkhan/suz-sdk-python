# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

[Unreleased]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/stemirkhan/suz-sdk-python/releases/tag/v0.1.0
