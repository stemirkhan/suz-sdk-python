# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

[Unreleased]: https://github.com/stemirkhan/suz-sdk-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/stemirkhan/suz-sdk-python/releases/tag/v0.1.0
