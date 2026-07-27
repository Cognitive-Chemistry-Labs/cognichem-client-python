# Changelog

## 1.0.0 — 2026-07-27

Clean-break redesign of the public SDK against the current CogniChem `/api/v1` compute API.

### Breaking changes (vs 0.1.x)

- Renamed facade: `CogniChemClient` → `CogniChem` (async: `AsyncCogniChem`).
- Renamed `client.utility` → `client.utils`.
- Dropped `requests`; transport is **httpx** with timeouts and connection reuse.
- Requires **Python ≥ 3.10**.
- Errors parse RFC 7807 `detail` (no longer the legacy `"default"` key).
- Job polling treats `cancelled` as terminal and uses finite timeouts (no infinite loops).
- Package layout moved to `src/cognichem_client/`.

### Added

- Full route coverage: batch job/inference submit, job info, multi-result ZIP, usage limits, auth, API key CRUD/rotate.
- Nested `client.inference.models.mpnn` for public/user MPNN model metadata.
- `Idempotency-Key` support on submit endpoints.
- Typed Pydantic response models and catalog constants (`JOB_TYPES`, `UTILITY_TYPES`, resources, terminal statuses).
- `wait` / `run` helpers with configurable poll interval and timeout.
- `CogniChem.from_env()` (`COGNICHEM_API_KEY`, `COGNICHEM_BASE_URL`, …).
- Unit tests (pytest + respx), ruff/mypy, CI, route-map drift check.

### Not included

- Billing/wallet APIs (website-only).
- Local payload validation via `cognichem-job-catalog` (optional future extras).
