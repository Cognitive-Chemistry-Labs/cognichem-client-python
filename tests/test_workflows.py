from __future__ import annotations

import json

import httpx
import pytest
import respx

from cognichem_client import AsyncCogniChem, CogniChem
from cognichem_client.errors import ProcessFailedError, ValidationError

BASE = "https://api.test.cognichem.com"
API = f"{BASE}/api/v1"

SPEC = {
    "spec_version": 1,
    "name": "vina-boltz-linear",
    "params": {},
    "steps": [
        {"id": "dock", "type": "job", "job_type": "autodockvina", "inputs": {}},
    ],
}


def _run(status: str, **extra: object) -> dict[str, object]:
    return {
        "id": "run-1",
        "run_name": "demo",
        "status": status,
        "steps": [
            {"id": "s1", "step_key": "dock", "status": status, "job_id": "job-1"}
        ],
        **extra,
    }


@respx.mock
def test_validate_and_estimate() -> None:
    validate = respx.post(f"{API}/workflows/validate").mock(
        return_value=httpx.Response(
            200,
            json={
                "valid": False,
                "errors": [
                    {"code": "cycle_detected", "message": "cycle", "step_id": "dock"}
                ],
                "warnings": [],
                "order": [],
                "step_count": 1,
            },
        )
    )
    respx.post(f"{API}/workflows/estimate").mock(
        return_value=httpx.Response(
            200,
            json={
                "total": 1.25,
                "per_step": [{"step_id": "dock", "cost": 1.25}],
                "tier": 1,
                "assumptions": [{"step_id": "dock", "reason": "static"}],
            },
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)

    result = client.workflows.validate(SPEC, params={"ligands": "CCO"})
    assert result.valid is False
    assert result.errors[0].code == "cycle_detected"
    body = json.loads(validate.calls.last.request.content)
    assert body == {"spec": SPEC, "params": {"ligands": "CCO"}}

    estimate = client.workflows.estimate(SPEC)
    assert estimate.total == 1.25
    assert estimate.per_step[0].step_id == "dock"


@respx.mock
def test_estimate_diagnostics_raise_validation_error() -> None:
    respx.post(f"{API}/workflows/estimate").mock(
        return_value=httpx.Response(
            422,
            json={
                "type": "/api/v1/problems/http-422",
                "title": "Unprocessable Content",
                "status": 422,
                "detail": "1 validation error",
                "errors": [{"code": "estimate_failed", "message": "nope"}],
                "retryability": "validation",
            },
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    with pytest.raises(ValidationError) as exc:
        client.workflows.estimate(SPEC)
    assert exc.value.errors == [{"code": "estimate_failed", "message": "nope"}]
    assert exc.value.retryability == "validation"


@respx.mock
def test_templates_and_node_ports() -> None:
    respx.get(f"{API}/workflows/templates").mock(
        return_value=httpx.Response(
            200,
            json={
                "templates": [
                    {
                        "id": "smiles-embed-dock",
                        "name": "SMILES to dock",
                        "summary": "Embed then dock",
                        "complexity": "simple",
                        "steps": [{"id": "dock", "type": "job"}],
                        "params": ["ligands"],
                    }
                ]
            },
        )
    )
    respx.get(f"{API}/workflows/templates/smiles-embed-dock").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "smiles-embed-dock",
                "name": "SMILES to dock",
                "summary": "Embed then dock",
                "complexity": "simple",
                "spec": SPEC,
            },
        )
    )
    ports = respx.get(f"{API}/workflows/node-ports").mock(
        return_value=httpx.Response(
            200,
            json={"job_type": "padel-descriptor", "inputs": {"m": {}}, "outputs": {}},
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    templates = client.workflows.templates()
    assert [t.id for t in templates] == ["smiles-embed-dock"]
    assert client.workflows.template("smiles-embed-dock").spec == SPEC
    assert client.workflows.node_ports("padel-descriptor").inputs == {"m": {}}
    assert ports.calls.last.request.url.params["job_type"] == "padel-descriptor"


@respx.mock
def test_run_create_sends_generated_idempotency_key() -> None:
    route = respx.post(f"{API}/workflows/runs").mock(
        return_value=httpx.Response(200, json=_run("pending", estimated_cost=2.5))
    )
    client = CogniChem(api_key="k", base_url=BASE)
    run = client.workflows.runs.create(
        "demo", SPEC, params={"ligands": "CCO"}, max_run_cost=5.0
    )
    assert run.estimated_cost == 2.5
    request = route.calls.last.request
    assert request.headers["Idempotency-Key"]
    assert json.loads(request.content) == {
        "run_name": "demo",
        "spec": SPEC,
        "params": {"ligands": "CCO"},
        "max_run_cost": 5.0,
    }

    client.workflows.runs.create("demo", SPEC, idempotency_key="mine")
    assert route.calls.last.request.headers["Idempotency-Key"] == "mine"


@respx.mock
def test_run_list_get_artifacts_resume_cancel_delete() -> None:
    listing = respx.get(f"{API}/workflows/runs").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [{"id": "run-1", "run_name": "demo", "status": "running"}],
                "total": 1,
                "limit": 10,
                "offset": 0,
            },
        )
    )
    get = respx.get(f"{API}/workflows/runs/run-1").mock(
        return_value=httpx.Response(200, json=_run("running", spec=SPEC))
    )
    respx.get(f"{API}/workflows/runs/run-1/artifacts").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "artifact_id": "art-1",
                        "step_key": "dock",
                        "port": "poses",
                        "data_kind": "docking_poses",
                        "data_format": "pdbqt",
                    }
                ]
            },
        )
    )
    respx.post(f"{API}/workflows/runs/run-1/resume").mock(
        return_value=httpx.Response(200, json=_run("running"))
    )
    respx.post(f"{API}/workflows/runs/run-1/cancel").mock(
        return_value=httpx.Response(
            200,
            json={
                "run_id": "run-1",
                "status": "cancelled",
                "cancelled_job_ids": ["job-1"],
                "message": "cancelled",
            },
        )
    )
    respx.delete(f"{API}/workflows/runs/run-1").mock(return_value=httpx.Response(204))
    client = CogniChem(api_key="k", base_url=BASE)

    page = client.workflows.runs.list(limit=10, status="running")
    assert page.items[0].id == "run-1"
    assert listing.calls.last.request.url.params["status"] == "running"
    assert "offset" not in listing.calls.last.request.url.params

    run = client.workflows.runs.get("run-1", include_spec=True)
    assert run.spec == SPEC
    assert run.steps[0].step_key == "dock"
    assert get.calls.last.request.url.params["include_spec"] == "1"

    assert client.workflows.runs.artifacts("run-1").items[0].artifact_id == "art-1"
    assert client.workflows.runs.resume("run-1").status == "running"
    assert client.workflows.runs.cancel("run-1").cancelled_job_ids == ["job-1"]
    assert client.workflows.runs.delete("run-1") is None


@respx.mock
def test_run_waits_and_stops_on_paused() -> None:
    respx.post(f"{API}/workflows/runs").mock(
        return_value=httpx.Response(200, json=_run("pending"))
    )
    statuses = iter([_run("running"), _run("paused", status_message="cap")])
    respx.get(f"{API}/workflows/runs/run-1").mock(
        side_effect=lambda request: httpx.Response(200, json=next(statuses))
    )
    client = CogniChem(api_key="k", base_url=BASE)
    run = client.workflows.runs.run("demo", SPEC, poll_interval=0.01, timeout=2.0)
    assert run.status == "paused"


@respx.mock
def test_run_raises_when_failed() -> None:
    respx.get(f"{API}/workflows/runs/run-1").mock(
        return_value=httpx.Response(
            200, json=_run("failed", status_message="step dock failed")
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    with pytest.raises(ProcessFailedError, match="step dock failed"):
        client.workflows.runs.wait(
            "run-1", poll_interval=0.01, timeout=1.0, raise_on_failure=True
        )


@respx.mock
def test_definitions_crud_share_versions() -> None:
    definition = {
        "id": "wfd-1",
        "user_id": "u-1",
        "name": "triage",
        "description": "",
        "spec": SPEC,
        "spec_version": 1,
    }
    create = respx.post(f"{API}/workflows/definitions").mock(
        return_value=httpx.Response(201, json=definition)
    )
    respx.get(f"{API}/workflows/definitions").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [{k: v for k, v in definition.items() if k != "spec"}],
                "total": 1,
                "limit": 50,
                "offset": 0,
            },
        )
    )
    update = respx.patch(f"{API}/workflows/definitions/wfd-1").mock(
        return_value=httpx.Response(200, json={**definition, "name": "v2"})
    )
    respx.delete(f"{API}/workflows/definitions/wfd-1").mock(
        return_value=httpx.Response(204)
    )
    respx.get(f"{API}/workflows/definitions/wfd-1/download").mock(
        return_value=httpx.Response(
            200,
            content=json.dumps(SPEC).encode(),
            headers={"Content-Disposition": "attachment; filename=triage.json"},
        )
    )
    respx.post(f"{API}/workflows/definitions/wfd-1/share").mock(
        return_value=httpx.Response(
            200, json={**definition, "visibility": "link", "share_token": "tok"}
        )
    )
    respx.delete(f"{API}/workflows/definitions/wfd-1/share").mock(
        return_value=httpx.Response(200, json=definition)
    )
    respx.get(f"{API}/workflows/definitions/shared/tok").mock(
        return_value=httpx.Response(200, json={"spec": SPEC})
    )
    fork = respx.post(f"{API}/workflows/definitions/shared/tok/fork").mock(
        return_value=httpx.Response(201, json={**definition, "id": "wfd-2"})
    )
    respx.get(f"{API}/workflows/definitions/wfd-1/versions").mock(
        return_value=httpx.Response(
            200,
            json={"items": [{"version": 2}], "total": 1, "limit": 50, "offset": 0},
        )
    )
    respx.get(f"{API}/workflows/definitions/wfd-1/versions/1").mock(
        return_value=httpx.Response(
            200, json={"definition_id": "wfd-1", "version": 1, "spec": SPEC}
        )
    )
    respx.post(f"{API}/workflows/definitions/wfd-1/versions/1/restore").mock(
        return_value=httpx.Response(200, json=definition)
    )
    client = CogniChem(api_key="k", base_url=BASE)
    defs = client.workflows.definitions

    assert defs.create("triage", SPEC, graph_layout={"nodes": {}}).id == "wfd-1"
    assert json.loads(create.calls.last.request.content)["graph_layout"] == {
        "nodes": {}
    }
    assert create.calls.last.request.headers["Idempotency-Key"]
    assert defs.list().items[0].name == "triage"
    assert defs.update("wfd-1", name="v2").name == "v2"
    assert json.loads(update.calls.last.request.content) == {"name": "v2"}
    with pytest.raises(ValueError):
        defs.update("wfd-1")
    assert defs.delete("wfd-1") is None
    exported = defs.download("wfd-1")
    assert json.loads(exported.content) == SPEC
    assert exported.filename == "triage.json"
    assert defs.share("wfd-1").share_token == "tok"
    assert defs.unshare("wfd-1").visibility == "private"
    assert defs.get_shared("tok") == {"spec": SPEC}
    assert defs.fork_shared("tok", "mine").id == "wfd-2"
    assert json.loads(fork.calls.last.request.content)["name"] == "mine"
    assert defs.versions("wfd-1").items[0].version == 2
    assert defs.get_version("wfd-1", 1).spec == SPEC
    assert defs.restore_version("wfd-1", 1).id == "wfd-1"


@respx.mock
async def test_async_workflow_run() -> None:
    respx.post(f"{API}/workflows/runs").mock(
        return_value=httpx.Response(200, json=_run("pending"))
    )
    respx.get(f"{API}/workflows/runs/run-1").mock(
        return_value=httpx.Response(200, json=_run("completed"))
    )
    respx.post(f"{API}/workflows/validate").mock(
        return_value=httpx.Response(
            200, json={"valid": True, "order": ["dock"], "step_count": 1}
        )
    )
    async with AsyncCogniChem(api_key="k", base_url=BASE) as client:
        assert (await client.workflows.validate(SPEC)).valid
        run = await client.workflows.runs.run(
            "demo", SPEC, poll_interval=0.01, timeout=1.0
        )
    assert run.status == "completed"
