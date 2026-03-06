# suz-sdk-python

Python SDK for the **СУЗ API 3.0** (СУЗ-Облако 4.0, API version 3.0.33).

Wraps the CRPT marking-code system HTTP API with a clean, typed Python interface.
This is **Iteration 1** — the core foundation.  See [Scope](#scope) for what is and is not implemented yet.

---

## Installation

```bash
pip install -e ".[dev]"   # development install with test dependencies
```

Requires Python 3.11+.

---

## Quick start

```python
from suz_sdk import SuzClient, Environment

client = SuzClient(
    oms_id="cdf12109-10d3-11e6-8b6f-0050569977a1",
    environment=Environment.SANDBOX,
    client_token="your-client-token",  # obtain via auth flow
)

info = client.health.ping()
print(info.oms_version)   # e.g. "3.1.8.0"
print(info.api_version)   # e.g. "2.0.0.54"
```

---

## Configuration

`SuzClient` accepts all settings as constructor arguments:

| Argument           | Type                  | Default   | Description                                            |
|--------------------|-----------------------|-----------|--------------------------------------------------------|
| `oms_id`           | `str`                 | required  | UUID of the СУЗ instance (`omsId` query parameter)     |
| `environment`      | `Environment`         | `SANDBOX` | Selects default base URL                               |
| `base_url`         | `str \| None`         | `None`    | Explicit base URL override (instance-specific)         |
| `client_token`     | `str \| None`         | `None`    | Pre-obtained `clientToken` for auth                    |
| `signer`           | `BaseSigner \| None`  | `None`    | Signer for `X-Signature` header                        |
| `oms_connection`   | `str \| None`         | `None`    | UUID of the registered integration installation        |
| `registration_key` | `str \| None`         | `None`    | Registration key from CRPT                             |
| `timeout`          | `float`               | `30.0`    | HTTP timeout in seconds                                |
| `verify_ssl`       | `bool`                | `True`    | TLS certificate verification                           |

### Environments

| Constant                 | Base URL (confirmed for registration endpoint) |
|--------------------------|------------------------------------------------|
| `Environment.SANDBOX`    | `https://suz-integrator.sandbox.crptech.ru`    |
| `Environment.PRODUCTION` | `https://suzgrid.crpt.ru:16443`                |

> **Note:** The main API URL (for ping, orders, etc.) is instance-specific
> in the СУЗ documentation (`<url стенда>`).  Supply your own `base_url`
> if your OMS instance uses a different address.

---

## Auth flow

The СУЗ API uses a `clientToken` security token (§9.1 of the API PDF).

Key facts:
- Each integration installation (`omsConnection`) has **exactly one** active token at a time
- Re-issuing a token **invalidates** the previous one
- Token TTL via True API (GIS MT): **10 hours**
- Token TTL via IS MDLP: specified in the token response

**Iteration 1** requires you to supply `client_token` manually.
**Iteration 2** will add `TokenManager` with automatic refresh.

```python
# For now, obtain the token externally and pass it in:
client = SuzClient(
    oms_id="...",
    client_token="1cecc8fb-fb47-4c8a-af3d-d34c1ead8c4f",
)
```

---

## Signing abstraction

Some endpoints require a request signature in the `X-Signature` HTTP header.

Requirements (§2.3.1 of the API PDF):
- Format: **detached CMS** (IETF RFC 5652), **not** attached (server returns HTTP 413 for attached)
- Algorithm: Russian GOST (GOST R 34.10-2012, GOST R 34.11-2012)
- Encoding: Base64
- For GET requests: sign `REQUEST_PATH + QUERY_STRING`
- For POST requests: sign the raw JSON body bytes

### Implementing a signer

```python
from suz_sdk import BaseSigner

class MyCryptoProSigner:
    def sign_bytes(self, payload: bytes) -> str:
        # Call your CryptoPro CLI or library here
        return base64_encoded_detached_cms_signature

client = SuzClient(
    oms_id="...",
    signer=MyCryptoProSigner(),
)
```

### NoopSigner (testing only)

```python
from suz_sdk import NoopSigner

# Returns empty string — will be rejected by the real server
# for endpoints that require X-Signature
client = SuzClient(oms_id="...", signer=NoopSigner())
```

---

## Exception handling

All SDK exceptions derive from `SuzError`:

```
SuzError
├── SuzTransportError       # network failure
│   └── SuzTimeoutError     # request timed out
├── SuzAuthError            # HTTP 401
│   └── SuzTokenExpiredError
├── SuzSignatureError       # HTTP 413 (attached signature rejected)
├── SuzValidationError      # HTTP 400
├── SuzApiError             # other non-2xx (has .status_code, .error_code, .raw_body)
└── SuzRateLimitError
```

```python
from suz_sdk import SuzClient, SuzApiError, SuzAuthError, SuzTimeoutError

try:
    info = client.health.ping()
except SuzTimeoutError:
    print("Request timed out")
except SuzAuthError:
    print("Token is invalid or expired")
except SuzApiError as e:
    print(f"API error {e.status_code}: {e}")
```

---

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

---

## Scope

### Iteration 1 — Foundation (this release)

- `pyproject.toml` and package structure under `src/suz_sdk/`
- `SuzClient` entry point
- `SuzConfig` + `Environment`
- Typed exception hierarchy
- `BaseSigner` Protocol + `NoopSigner`
- `HttpxTransport` with full error mapping
- `client.health.ping()` — availability and version check

### Not yet implemented (future iterations)

- `TokenManager` — auto-refresh, TTL tracking, thread-safe renewal
- `client.integration.register_connection()`
- `client.auth.authenticate()`
- `client.orders.*` — create, get_status, get_codes, close
- `client.reports.*` — send_utilisation, get_status
- `client.receipts.*`
- Async client
- CryptoPro signer integration

---

## Architecture

```
src/suz_sdk/
├── __init__.py              # public API surface
├── client.py                # SuzClient entry point
├── config.py                # SuzConfig + Environment
├── exceptions.py            # typed exception hierarchy
├── signing/
│   ├── base.py              # BaseSigner Protocol
│   └── noop.py              # NoopSigner
├── transport/
│   ├── base.py              # BaseTransport Protocol + Request/Response
│   └── httpx_transport.py   # httpx-backed implementation
└── api/
    └── health.py            # HealthApi.ping()
```

Layer responsibilities:

| Layer         | Responsibility                                         |
|---------------|--------------------------------------------------------|
| `transport`   | HTTP mechanics, timeouts, response parsing, error mapping |
| `signing`     | `bytes → Base64 detached CMS signature`               |
| `api`         | High-level typed methods (business logic)              |
| `client`      | Wires layers together, injects auth headers            |
