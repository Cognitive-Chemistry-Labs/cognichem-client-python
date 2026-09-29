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
| **JWT** (API key management, Assistant chat) | `client.auth.login_email(email, password)` or `CogniChem(access_token=...)` |

API keys carry `read` and/or `write` scopes. Submitting jobs, workflow runs, or uploads needs `write`. API-key mutations must send an `Idempotency-Key`; the client generates one per call unless you pass `idempotency_key=` (pass your own to make retries safe).

Environment variables:

- `COGNICHEM_API_KEY`
- `COGNICHEM_ACCESS_TOKEN` (optional Bearer)
- `COGNICHEM_BASE_URL` (default `https://api.cognichem.com`)

Create and manage keys in your [CogniChem account](https://cognichem.com). Collection endpoints under `/auth/api-keys` require JWT.

## API surface

| Resource | Methods |
|----------|---------|
| `client.jobs` | `submit`, `submit_many`, `estimate`, `wait`, `run`, `result`, `result_many`, `info`, `status`, `list` (paginated, filters), `cancel`, `delete` |
| `client.workflows` | `validate`, `estimate`, `templates`, `template`, `node_ports` |
| `client.workflows.runs` | `create`, `list`, `get`, `artifacts`, `resume`, `cancel`, `delete`, `wait`, `run` |
| `client.workflows.definitions` | `create`, `list`, `get`, `update`, `delete`, `download`, `share`, `unshare`, `get_shared`, `fork_shared`, `versions`, `get_version`, `restore_version` |
| `client.artifacts` | `list`, `usage`, `upload`, `get`, `download` (whole zip or one `record=`), `delete` |
| `client.events` | `list`, `listen` (long-poll completion events for jobs and workflow runs) |
| `client.wallet` | `balance` |
| `client.lookup` | `pubchem`, `chembl`, `targets` (Open Targets), `uniprot`, `pdb`, `properties` |
| `client.reference` | `search`, `get`, `neighborhood` (literature / method papers) |
| `client.chat` (JWT) | `estimate`, `stream`, `send`, `stop`, `spend_cap`, `continue_spend_cap`, plus `sessions.*` and `proposals.*` |
| `client.inference` | `submit`, `submit_batch`, `wait`, `run`, `result`, `list`, `cancel`, `delete` |
| `client.inference.models.mpnn` | `public()`, `user(name=None)`, `delete(name)` |
| `client.utils` | `submit`, `wait`, `run`, `result`, `list`, `cancel`, `delete` |
| `client.usage` | `limits(month=None)` |
| `client.auth` / `client.api_keys` | login, check, refresh, logout; list/create/get/update/rename/rotate/delete keys |
| `client` | `health()`, `ready()` |

Async twin: `AsyncCogniChem` with the same method names (`await client.jobs.run(...)`, `async for event in client.chat.stream(...)`).

## Workflows

```python
from cognichem_client import CogniChem, artifact_ref

client = CogniChem.from_env()

spec = client.workflows.template("smiles-embed-dock").spec
target = client.artifacts.upload("target.pdb", data_kind="protein_structure", data_format="pdb")
params = {
    "ligands": ["CCO", "c1ccccc1O"],
    "target_structure": artifact_ref(target.id, "structure"),
}

assert client.workflows.validate(spec, params=params).valid
estimate = client.workflows.estimate(spec, params=params)  # USD hold at your tier

run = client.workflows.runs.run("dock-demo", spec, params=params, max_run_cost=estimate.total * 1.5)
# run.status is "completed" (or "paused" if it hit max_run_cost; call runs.resume)
for item in client.workflows.runs.artifacts(run.id).items:
    print(item.step_key, item.port, item.artifact_id, item.record_count)
```

`runs.wait` stops on `completed`, `failed`, `cancelled`, or `paused` (a paused run needs you to resume it). `runs.run` raises `ProcessFailedError` / `ProcessCancelledError` on failure.

Job and run outputs are durable **artifacts**: `client.jobs.status(pid).result_artifact_id` points at one. Inspect the manifest with `client.artifacts.get(...)` and fetch single records with `download(..., record=...)` instead of whole zips. Bind artifacts into workflow params or job payloads with `artifact_ref(id, port)`.

## Completion events

```python
for event in client.events.listen(kind="workflow_run"):
    print(event.subject_id, event.status)  # re-read the run for detail
```

## CogniChem Assistant (JWT)

```python
client = CogniChem(access_token=token)
session = client.chat.sessions.create("Docking plan")
reply = client.chat.send(session.id, "Dock aspirin against COX-1", reasoning_effort="low")
print(reply.content, reply.billed_usd)
for proposal in client.chat.proposals.list(session.id).items:
    client.chat.proposals.approve(session.id, proposal.id, proposal.estimate_usd)
```

Each turn holds wallet funds at your tier's token rate and bills the metered tokens. A thread at its spend cap raises `ConflictError` (`code == "session-spend-cap"`); `continue_spend_cap` raises the cap.

## Errors

API failures raise subclasses of `CogniChemError` parsed from RFC 7807 problem details (`detail`, `title`, `status`, `type`, `request_id`, `retryability`, `errors`). `code` is the problem type slug (for example `missing-idempotency-key`, `insufficient-scope`, `spend-ceiling-exceeded`, `insufficient-wallet`, `session-spend-cap`, `estimate-changed`), and `body` holds any extra fields.

| Status | Exception |
|--------|-----------|
| 400 | `BadRequestError` |
| 401 | `AuthenticationError` |
| 402 | `PaymentRequiredError` |
| 403 | `ForbiddenError` |
| 404 | `NotFoundError` |
| 409 | `ConflictError` |
| 410 | `GoneError` |
| 413 | `PayloadTooLargeError` |
| 422 | `ValidationError` (WorkflowSpec diagnostics in `errors`) |
| 429 | `RateLimitError` |
| 5xx | `ServerError` |

Polling helpers raise `PollTimeoutError`, `ProcessFailedError`, or `ProcessCancelledError` when appropriate.

## Examples

See [`examples/`](examples/) for scripts covering utilities, inference, job submission, workflow templates, artifact records, science lookups, and the Assistant.

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
# refresh the ROUTE_MAP snapshot from a monorepo checkout:
python scripts/sync_routes.py --backend-config ../cognichem/apps/back-end-api/src/core/config.py --write-snapshot
```

## Migrating from 0.1.x

**1.0 is a clean break.** There is no compatibility shim for `CogniChemClient` / `client.utility`. See [CHANGELOG.md](CHANGELOG.md).

## License

Apache 2.0
