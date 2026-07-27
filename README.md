![CogniChem Logo](https://cognichem.com/images/cc-logo-color.svg)

# CogniChem Python Client

[![PyPI version](https://badge.fury.io/py/cognichem-client.svg)](https://badge.fury.io/py/cognichem-client)
[![GitHub license](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/Cognitive-Chemistry-Labs/cognichem-client-python/blob/main/LICENSE)

Official Python SDK for the [CogniChem](https://cognichem.com) compute API (`/api/v1`).

## Installation

```bash
pip install cognichem-client
```

Requires **Python 3.10+**.

## Quick start

```python
from cognichem_client import CogniChem

client = CogniChem(api_key="YOUR_API_KEY")
# or: CogniChem.from_env()  # reads COGNICHEM_API_KEY / COGNICHEM_BASE_URL

# Short utility
result = client.utils.run(
    "convert",
    {
        "input_data": "CCO",
        "input_format": "smiles",
        "output_format": "pdbblock",
    },
)
print(result.data)

# Long-running job: submit → wait → download
submitted = client.jobs.submit(
    job_name="my-padel-run",
    job_type="padel-descriptor",
    payload={
        "input_data": ["CCO", "CCC"],
        "input_format": "smiles",
        "descriptor_types": ["ALOGP", "AtomCount"],
    },
)
status = client.jobs.wait(submitted.process_id)  # completed | error | cancelled
if status.status == "completed":
    artifact = client.jobs.result(submitted.process_id, save_path="./")
    print(artifact.filename)
```

## Authentication

| Mode | How |
|------|-----|
| **API key** (recommended for scripts) | `CogniChem(api_key=...)` → `X-Api-Key` header |
| **JWT** (API key management) | `client.auth.login_email(email, password)` then `client.api_keys.*` |

Environment variables:

- `COGNICHEM_API_KEY`
- `COGNICHEM_ACCESS_TOKEN` (optional Bearer)
- `COGNICHEM_BASE_URL` (default `https://api.cognichem.com`)

Create and manage keys in your [CogniChem account](https://cognichem.com). Collection endpoints under `/auth/api-keys` require JWT.

## API surface

| Resource | Examples |
|----------|----------|
| `client.jobs` | `submit`, `submit_many`, `wait`, `run`, `result`, `result_many`, `info`, `list`, `cancel`, `delete` |
| `client.inference` | `submit`, `submit_batch`, `wait`, `run`, `result`, `list`, `delete` |
| `client.inference.models.mpnn` | `public()`, `user(name=None)`, `delete(name)` |
| `client.utils` | `submit`, `wait`, `run`, `result`, `list`, `delete` |
| `client.usage` | `limits(month=None)` |
| `client.auth` / `client.api_keys` | login, check, refresh, logout; list/create/rotate/delete keys |

Optional `idempotency_key=` on mutating POSTs (`jobs`, `inference`, `utils` submit).

Async twin: `AsyncCogniChem` with the same method names (`await client.jobs.run(...)`).

## Errors

API failures raise subclasses of `CogniChemError` parsed from RFC 7807 problem details (`detail`, `title`, `status`, `type`, `request_id`, `errors` on 422).

Polling helpers raise `PollTimeoutError`, `ProcessFailedError`, or `ProcessCancelledError` when appropriate.

## Examples

See [`examples/`](examples/) for scripts covering utilities, inference, and job submission.

Live OpenAPI docs: [https://api.cognichem.com/docs](https://api.cognichem.com/docs)

## Development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check src tests
mypy
pytest
python scripts/sync_routes.py
```

## Migrating from 0.1.x

**1.0 is a clean break.** There is no compatibility shim for `CogniChemClient` / `client.utility`. See [CHANGELOG.md](CHANGELOG.md).

## License

Apache 2.0
