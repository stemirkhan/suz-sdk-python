# AGENTS.md

## Source of Truth

Always use these documents as the primary source of truth:

1. `docs/technical_specification.md`
2. `docs/API_СУЗ_3.0.pdf`

If implementation details conflict with these documents, follow the documents.

Do not invent endpoints, payload fields, authentication rules, or business flows.

## Current Priority

Current priority is to build a solid SDK foundation and MVP, not full API coverage.

Focus on:
- project structure
- config
- exceptions
- transport
- sync client
- signing abstraction
- token management foundation
- health endpoint
- tests
- README

## Technical Rules

- Python 3.11+
- Strong typing required
- Pydantic v2 for models
- `httpx` for transport
- `pytest` for tests
- English docstrings and code comments
- Keep dependencies minimal and justified

## Architecture Rules

Keep responsibilities separated:

- `client.py` — public SDK entry point
- `config.py` — configuration
- `exceptions.py` — typed exceptions
- `transport/` — HTTP layer
- `auth/` — token/auth logic
- `signing/` — signing abstraction
- `models/` — Pydantic models
- `api/` — high-level endpoint clients

Do not mix transport, auth, and business logic in one file.

## Change Rules

Before coding:
1. Read the relevant files in `docs/`
2. Inspect the current repository structure
3. Summarize the plan briefly
4. Make focused changes
5. Report what was changed and what remains

Do not pretend unclear parts are fully implemented.
If something is uncertain, leave a clear TODO with explanation.

## Testing Rules

Add tests for meaningful infrastructure changes where practical.

Prioritize tests for:
- config validation
- exception mapping
- transport behavior
- token manager behavior
- header construction
- signing integration points
- health endpoint behavior