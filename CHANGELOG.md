# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

[Unreleased]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/stemirkhan/suz-sdk-python/releases/tag/v0.1.0
