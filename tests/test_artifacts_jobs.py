from __future__ import annotations

import json

import httpx
import pytest
import respx

from cognichem_client import AsyncCogniChem, CogniChem

BASE = "https://api.test.cognichem.com"
API = f"{BASE}/api/v1"

ARTIFACT = {
    "id": "art-1",
    "job_id": "job-1",
    "size_bytes": 10,
    "content_type": "application/zip",
    "manifest": {"ports": {"poses": {"records": [{"id": "lig-1"}]}}},
}


@respx.mock
def test_artifacts_list_usage_get_delete() -> None:
    listing = respx.get(f"{API}/artifacts").mock(
        return_value=httpx.Response(
            200,
            json={
                "items": [
                    {
                        "artifact_id": "art-1",
                        "port": "poses",
                        "data_kind": "docking_poses",
                        "data_format": "pdbqt",
                        "record_count": 1,
                    }
                ],
                "has_more": True,
                "next_offset": 25,
            },
        )
    )
    respx.get(f"{API}/artifacts/usage").mock(
        return_value=httpx.Response(
            200,
            json={
                "used_bytes": 1,
                "quota_bytes": 10,
                "artifact_count": 1,
                "tier": 2,
            },
        )
    )
    respx.get(f"{API}/artifacts/art-1").mock(
        return_value=httpx.Response(200, json=ARTIFACT)
    )
    respx.delete(f"{API}/artifacts/art-1").mock(
        return_value=httpx.Response(200, json={"message": "Artifact art-1 deleted"})
    )
    client = CogniChem(api_key="k", base_url=BASE)

    page = client.artifacts.list(data_kind="docking_poses", include_archive=True)
    assert page.items[0].artifact_id == "art-1"
    assert page.next_offset == 25
    params = listing.calls.last.request.url.params
    assert params["data_kind"] == "docking_poses"
    assert params["include_archive"] == "true"
    assert "limit" not in params

    assert client.artifacts.usage().tier == 2
    assert client.artifacts.get("art-1").manifest["ports"]["poses"]
    assert "deleted" in client.artifacts.delete("art-1").message


@respx.mock
def test_artifact_record_download(tmp_path) -> None:  # type: ignore[no-untyped-def]
    route = respx.get(f"{API}/artifacts/art-1/download").mock(
        return_value=httpx.Response(
            200,
            content=b"ATOM",
            headers={"Content-Disposition": "attachment; filename=lig-1.pdbqt"},
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    result = client.artifacts.download(
        "art-1", record="lig-1", port="poses", save_path=tmp_path
    )
    assert result.content == b"ATOM"
    assert (tmp_path / "lig-1.pdbqt").read_bytes() == b"ATOM"
    assert route.calls.last.request.url.params["record"] == "lig-1"
    assert route.calls.last.request.url.params["port"] == "poses"


@respx.mock
def test_artifact_upload_raw_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    route = respx.post(f"{API}/artifacts").mock(
        return_value=httpx.Response(201, json=ARTIFACT)
    )
    pdb = tmp_path / "target.pdb"
    pdb.write_text("ATOM      1  N\n")
    client = CogniChem(api_key="k", base_url=BASE)
    artifact = client.artifacts.upload(
        pdb, data_kind="protein_structure", data_format="pdb"
    )
    assert artifact.id == "art-1"
    request = route.calls.last.request
    assert request.headers["Content-Type"].startswith("multipart/form-data")
    assert request.headers["Idempotency-Key"]
    body = request.content
    assert b'name="mode"' in body and b"raw_file" in body
    assert b'filename="target.pdb"' in body
    assert b"protein_structure" in body

    with pytest.raises(ValueError):
        client.artifacts.upload(b"x", mode="raw_file")


@respx.mock
def test_job_estimate_list_filters_and_status_artifact() -> None:
    respx.post(f"{API}/jobs/estimate").mock(
        return_value=httpx.Response(
            200,
            json={
                "cost": 0.12,
                "tier": 1,
                "resource": "cpu",
                "job_type": "autodockvina",
                "expected_runtime_sec": 600.0,
                "rate_per_sec": 0.0002,
                "assumptions": {"validated": True},
            },
        )
    )
    listing = respx.get(f"{API}/jobs/list").mock(
        return_value=httpx.Response(
            200,
            json={
                "job_names": ["a"],
                "job_pids": ["job-a"],
                "items": [
                    {
                        "process_id": "job-a",
                        "job_name": "a",
                        "job_type": "autodockvina",
                        "resource": "cpu",
                        "status": "running",
                    }
                ],
                "total": 1,
                "limit": 20,
                "offset": 0,
            },
        )
    )
    respx.get(f"{API}/jobs/status").mock(
        return_value=httpx.Response(
            200,
            json={
                "process_id": "job-a",
                "status": "completed",
                "result_artifact_id": "art-1",
            },
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    estimate = client.jobs.estimate("autodockvina", {"x": 1}, resource="cpu")
    assert estimate.cost == 0.12

    page = client.jobs.list(limit=20, status=["queued", "running"], q="dock")
    assert page.items[0].status == "running"
    params = listing.calls.last.request.url.params
    assert params["status"] == "queued,running"
    assert params["q"] == "dock"
    assert "sort" not in params

    assert client.jobs.status("job-a").result_artifact_id == "art-1"


@respx.mock
def test_submit_generates_idempotency_key_per_call() -> None:
    route = respx.post(f"{API}/jobs/submit").mock(
        return_value=httpx.Response(200, json={"process_id": "job-1"})
    )
    client = CogniChem(api_key="k", base_url=BASE)
    client.jobs.submit("a", "padel-descriptor", {})
    client.jobs.submit("b", "padel-descriptor", {})
    keys = [call.request.headers["Idempotency-Key"] for call in route.calls]
    assert all(keys) and keys[0] != keys[1]


@respx.mock
def test_inference_and_utils_cancel() -> None:
    inference = respx.post(f"{API}/inference/cancel").mock(
        return_value=httpx.Response(200, json={"message": "cancelled"})
    )
    utils = respx.post(f"{API}/utils/cancel").mock(
        return_value=httpx.Response(200, json={"message": "cancelled"})
    )
    client = CogniChem(api_key="k", base_url=BASE)
    assert client.inference.cancel("inf-1").message == "cancelled"
    assert client.utils.cancel("util-1").message == "cancelled"
    assert inference.calls.last.request.url.params["process_id"] == "inf-1"
    assert utils.calls.last.request.url.params["process_id"] == "util-1"


@respx.mock
def test_api_keys_create_update_delete() -> None:
    key = {
        "id": "key-1",
        "name": "ci",
        "scopes": ["read"],
        "created_at": "2026-09-01T00:00:00Z",
        "allow_structure_search": True,
        "spend_ceiling_usd": 5.0,
    }
    create = respx.post(f"{API}/auth/api-keys").mock(
        return_value=httpx.Response(201, json={**key, "api_key": "secret"})
    )
    update = respx.patch(f"{API}/auth/api-keys/key-1").mock(
        return_value=httpx.Response(200, json=key)
    )
    respx.delete(f"{API}/auth/api-keys/key-1").mock(return_value=httpx.Response(204))
    client = CogniChem(access_token="jwt", base_url=BASE)
    created = client.api_keys.create(
        "ci",
        scopes=["read"],
        spend_ceiling_usd=5.0,
        allow_structure_search=True,
        expires_at="2027-01-01T00:00:00Z",
    )
    assert created.api_key == "secret"
    assert created.allow_structure_search is True
    assert json.loads(create.calls.last.request.content) == {
        "name": "ci",
        "scopes": ["read"],
        "expires_at": "2027-01-01T00:00:00Z",
        "spend_ceiling_usd": 5.0,
        "allow_structure_search": True,
    }
    assert create.calls.last.request.headers["Authorization"] == "Bearer jwt"

    client.api_keys.update("key-1", allow_structure_search=False)
    assert json.loads(update.calls.last.request.content) == {
        "allow_structure_search": False
    }
    client.api_keys.rename("key-1", "prod")
    assert json.loads(update.calls.last.request.content) == {"name": "prod"}
    assert client.api_keys.delete("key-1") is None


@respx.mock
def test_health_and_ready() -> None:
    respx.get(f"{BASE}/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    respx.get(f"{BASE}/ready").mock(
        return_value=httpx.Response(200, json={"status": "ready"})
    )
    client = CogniChem(api_key="k", base_url=BASE)
    assert client.health().status == "ok"
    assert client.ready().status == "ready"


@respx.mock
async def test_async_artifact_upload_bytes() -> None:
    route = respx.post(f"{API}/artifacts").mock(
        return_value=httpx.Response(201, json=ARTIFACT)
    )
    async with AsyncCogniChem(api_key="k", base_url=BASE) as client:
        artifact = await client.artifacts.upload(b"PK\x03\x04")
    assert artifact.id == "art-1"
    body = route.calls.last.request.content
    assert b"cognichem_zip" in body and b'filename="result.zip"' in body
