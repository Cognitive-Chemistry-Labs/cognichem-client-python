# Changelog

## 1.1.0 — 2026-09-28

Full coverage of the current `/api/v1` (Agent platform epic, cognichem#458; covers the Python-client follow-up cognichem#269). Additive: existing 1.0 calls keep working.

### Added

- **Workflows** (`client.workflows`): `validate`, `estimate`, curated `templates` / `template`, catalog `node_ports`.
  - `workflows.runs`: `create`, `list`, `get(include_spec=)`, `artifacts`, `resume`, `cancel`, `delete`, `wait`, `run`. `wait` stops on `completed | failed | cancelled | paused`.
  - `workflows.definitions`: CRUD, JSON `download`, link `share` / `unshare`, `get_shared` / `fork_shared`, `versions` / `get_version` / `restore_version`.
- **Artifacts** (`client.artifacts`): `list` (filters, paging), `usage`, `upload` (`cognichem_zip` or `raw_file` multipart), `get` (manifest), `download` (whole zip or one `record=`), `delete`. `artifact_ref(id, port)` builds `$artifact` bindings.
- **Completion events** (`client.events`): `list` and a long-polling, de-duplicating `listen` generator.
- **Wallet** (`client.wallet.balance`), **science lookups** (`client.lookup`: PubChem, ChEMBL, Open Targets, UniProt, RCSB PDB, PubChem properties), and the **reference KG** (`client.reference`: `search`, `get`, `neighborhood`).
- **CogniChem Assistant chat** (`client.chat`, JWT only): sessions, message history, turn `estimate`, SSE `stream` / collected `send`, `stop`, thread `spend_cap` / `continue_spend_cap`, and run `proposals` (`list`, `get`, `approve`, `reject`).
- Jobs: `estimate`; `list` pagination and filters (`limit`, `offset`, `status`, `job_type`, `q`, `sort`) with full `items` rows; `status().result_artifact_id`.
- Inference / utils: `cancel`.
- API keys: `create(scopes=, expires_at=, spend_ceiling_usd=, allow_structure_search=)`, `update(name=, allow_structure_search=)`; new key metadata fields.
- `client.health()` / `client.ready()`.
- Errors: `BadRequestError` (400), `PaymentRequiredError` (402), `GoneError` (410), `PayloadTooLargeError` (413), `ServerError` (5xx); `retryability` attribute; `code` is now the problem type slug (e.g. `missing-idempotency-key`, `session-spend-cap`).
- Catalog constants: 45 submittable job types (was 23), utilities `molecule_standardize`, `druglikeness_filter`, `coolprop`, workflow run statuses.

### Fixed

- Mutating calls (`jobs.submit`, `submit_many`, `inference.submit*`, `utils.submit`, run / definition / upload writes) now send an auto-generated `Idempotency-Key` when none is given. The API rejects API-key mutations without one (400 `missing-idempotency-key`), so 1.0 submits failed with API keys.
- `api_keys.delete` returns `None`; it raised on the API's 204 response.

### Changed

- `cognichem_client.types` is now a package (same import path; every model is still importable from it).
- `scripts/sync_routes.py` checks keys **and paths** against backend `ROUTE_MAP` (`scripts/route_map.txt`).

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
