from __future__ import annotations

import httpx
import pytest
import respx

from cognichem_client import CogniChem
from cognichem_client.errors import (
    PollTimeoutError,
    ProcessCancelledError,
    ProcessFailedError,
)
from cognichem_client.types import JobSubmitRequest

BASE = "https://api.test.cognichem.com"


@respx.mock
def test_submit_and_idempotency_header() -> None:
    route = respx.post(f"{BASE}/api/v1/jobs/submit").mock(
        return_value=httpx.Response(200, json={"process_id": "job-1"})
    )
    client = CogniChem(api_key="k", base_url=BASE)
    result = client.jobs.submit(
        "my-job",
        "train-mpnn",
        {"x": 1},
        resource="a10",
        idempotency_key="idem-1",
    )
    assert result.process_id == "job-1"
    assert route.calls.last.request.headers["Idempotency-Key"] == "idem-1"
    assert route.calls.last.request.headers["X-Api-Key"] == "k"
    body = route.calls.last.request.content
    assert b'"resource":"a10"' in body or b'"resource": "a10"' in body


@respx.mock
def test_submit_many_info_list_cancel_delete() -> None:
    respx.post(f"{BASE}/api/v1/jobs/submit-multiple").mock(
        return_value=httpx.Response(200, json={"process_ids": ["job-a", "job-b"]})
    )
    respx.get(f"{BASE}/api/v1/jobs/list").mock(
        return_value=httpx.Response(
            200, json={"job_names": ["a"], "job_pids": ["job-a"]}
        )
    )
    respx.get(f"{BASE}/api/v1/jobs/info").mock(
        return_value=httpx.Response(
            200, json={"process_id": "job-a", "info": {"status": "running"}}
        )
    )
    respx.delete(f"{BASE}/api/v1/jobs/cancel").mock(
        return_value=httpx.Response(200, json={"message": "cancelled"})
    )
    respx.delete(f"{BASE}/api/v1/jobs/delete").mock(
        return_value=httpx.Response(200, json={"message": "deleted"})
    )

    client = CogniChem(api_key="k", base_url=BASE)
    many = client.jobs.submit_many(
        [
            JobSubmitRequest(
                job_name="a", job_type="padel-descriptor", payload={"input_data": []}
            )
        ]
    )
    assert many.process_ids == ["job-a", "job-b"]
    assert client.jobs.list().job_pids == ["job-a"]
    assert client.jobs.info("job-a").info["status"] == "running"
    assert client.jobs.cancel("job-a").message == "cancelled"
    assert client.jobs.delete("job-a").message == "deleted"


@respx.mock
def test_result_binary_and_save(tmp_path) -> None:  # type: ignore[no-untyped-def]
    respx.get(f"{BASE}/api/v1/jobs/result").mock(
        return_value=httpx.Response(
            200,
            content=b"zip-bytes",
            headers={
                "Content-Type": "application/zip",
                "Content-Disposition": 'attachment; filename="out.zip"',
            },
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    result = client.jobs.result("job-1", save_path=tmp_path)
    assert result.content == b"zip-bytes"
    assert result.filename == "out.zip"
    assert (tmp_path / "out.zip").read_bytes() == b"zip-bytes"


@respx.mock
def test_result_many_zip() -> None:
    respx.get(f"{BASE}/api/v1/jobs/result-multiple").mock(
        return_value=httpx.Response(
            200,
            content=b"PK\x03\x04",
            headers={
                "Content-Type": "application/zip",
                "Content-Disposition": "attachment; filename=job_results.zip",
            },
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    result = client.jobs.result_many(["job-1", "job-2"])
    assert result.content.startswith(b"PK")
    assert result.filename == "job_results.zip"


@respx.mock
def test_wait_completed() -> None:
    statuses = iter(
        [
            {"process_id": "job-1", "status": "running", "message": None},
            {"process_id": "job-1", "status": "completed", "message": "ok"},
        ]
    )
    respx.get(f"{BASE}/api/v1/jobs/status").mock(
        side_effect=lambda request: httpx.Response(200, json=next(statuses))
    )
    client = CogniChem(api_key="k", base_url=BASE)
    final = client.jobs.wait("job-1", poll_interval=0.01, timeout=2.0)
    assert final.status == "completed"


@respx.mock
def test_wait_cancelled_terminal() -> None:
    respx.get(f"{BASE}/api/v1/jobs/status").mock(
        return_value=httpx.Response(
            200,
            json={"process_id": "job-1", "status": "cancelled", "message": "stopped"},
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    with pytest.raises(ProcessCancelledError):
        client.jobs.wait(
            "job-1", poll_interval=0.01, timeout=2.0, raise_on_failure=True
        )


@respx.mock
def test_run_raises_on_error() -> None:
    respx.post(f"{BASE}/api/v1/jobs/submit").mock(
        return_value=httpx.Response(200, json={"process_id": "job-1"})
    )
    respx.get(f"{BASE}/api/v1/jobs/status").mock(
        return_value=httpx.Response(
            200,
            json={"process_id": "job-1", "status": "error", "message": "boom"},
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    with pytest.raises(ProcessFailedError, match="boom"):
        client.jobs.run("n", "train-mpnn", {}, poll_interval=0.01, timeout=2.0)


@respx.mock
def test_wait_timeout() -> None:
    respx.get(f"{BASE}/api/v1/jobs/status").mock(
        return_value=httpx.Response(
            200,
            json={"process_id": "job-1", "status": "running", "message": None},
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    with pytest.raises(PollTimeoutError):
        client.jobs.wait("job-1", poll_interval=0.01, timeout=0.05)
