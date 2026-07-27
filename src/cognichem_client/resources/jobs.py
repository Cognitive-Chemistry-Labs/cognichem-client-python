from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import (
    DEFAULT_JOB_POLL_INTERVAL,
    DEFAULT_JOB_TIMEOUT,
    JOB_TERMINAL_STATUSES,
    ROUTES,
)
from cognichem_client.polling import await_for_terminal, wait_for_terminal
from cognichem_client.types import (
    BinaryResult,
    JobInfoResponse,
    JobSubmitMultipleResponse,
    JobSubmitRequest,
    JobSubmitResponse,
    ListJobsResponse,
    MessageResponse,
    ProcessStatus,
)


def _maybe_save(result: BinaryResult, save_path: str | Path | None) -> BinaryResult:
    if save_path is None:
        return result
    path = Path(save_path)
    if path.is_dir():
        filename = result.filename or "result.bin"
        path = path / filename
    path.write_bytes(result.content)
    return result


class JobsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def submit(
        self,
        job_name: str,
        job_type: str,
        payload: dict[str, Any],
        *,
        resource: str = "default",
        idempotency_key: str | None = None,
    ) -> JobSubmitResponse:
        data = self._http.request(
            "POST",
            ROUTES["jobs_submit"],
            json={
                "job_name": job_name,
                "job_type": job_type,
                "payload": payload,
                "resource": resource,
            },
            idempotency_key=idempotency_key,
        )
        return JobSubmitResponse.model_validate(data)

    def submit_many(
        self,
        jobs: Sequence[JobSubmitRequest | dict[str, Any]],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitMultipleResponse:
        body = {
            "jobs": [
                j.model_dump() if isinstance(j, JobSubmitRequest) else j for j in jobs
            ]
        }
        data = self._http.request(
            "POST",
            ROUTES["jobs_submit_multiple"],
            json=body,
            idempotency_key=idempotency_key,
        )
        return JobSubmitMultipleResponse.model_validate(data)

    def list(self) -> ListJobsResponse:
        data = self._http.request("GET", ROUTES["jobs_list"])
        return ListJobsResponse.model_validate(data)

    def info(self, process_id: str) -> JobInfoResponse:
        data = self._http.request(
            "GET", ROUTES["jobs_info"], params={"process_id": process_id}
        )
        return JobInfoResponse.model_validate(data)

    def status(self, process_id: str) -> ProcessStatus:
        data = self._http.request(
            "GET", ROUTES["jobs_status"], params={"process_id": process_id}
        )
        return ProcessStatus.model_validate(data)

    def result(
        self,
        process_id: str,
        *,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        result = self._http.request(
            "GET",
            ROUTES["jobs_result"],
            params={"process_id": process_id},
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    def result_many(
        self,
        process_ids: Sequence[str],
        *,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        result = self._http.request(
            "GET",
            ROUTES["jobs_result_multiple"],
            params={"process_ids": ",".join(process_ids)},
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    def cancel(self, process_id: str) -> MessageResponse:
        data = self._http.request(
            "DELETE", ROUTES["jobs_cancel"], params={"process_id": process_id}
        )
        return MessageResponse.model_validate(data)

    def delete(self, process_id: str) -> MessageResponse:
        data = self._http.request(
            "DELETE", ROUTES["jobs_delete"], params={"process_id": process_id}
        )
        return MessageResponse.model_validate(data)

    def wait(
        self,
        process_id: str,
        *,
        poll_interval: float = DEFAULT_JOB_POLL_INTERVAL,
        timeout: float = DEFAULT_JOB_TIMEOUT,
        raise_on_failure: bool = False,
    ) -> ProcessStatus:
        return wait_for_terminal(
            lambda: self.status(process_id),
            poll_interval=poll_interval,
            timeout=timeout,
            terminal_statuses=JOB_TERMINAL_STATUSES,
            raise_on_failure=raise_on_failure,
        )

    def run(
        self,
        job_name: str,
        job_type: str,
        payload: dict[str, Any],
        *,
        resource: str = "default",
        idempotency_key: str | None = None,
        poll_interval: float = DEFAULT_JOB_POLL_INTERVAL,
        timeout: float = DEFAULT_JOB_TIMEOUT,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        submitted = self.submit(
            job_name,
            job_type,
            payload,
            resource=resource,
            idempotency_key=idempotency_key,
        )
        self.wait(
            submitted.process_id,
            poll_interval=poll_interval,
            timeout=timeout,
            raise_on_failure=True,
        )
        return self.result(submitted.process_id, save_path=save_path)


class AsyncJobsResource:
    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def submit(
        self,
        job_name: str,
        job_type: str,
        payload: dict[str, Any],
        *,
        resource: str = "default",
        idempotency_key: str | None = None,
    ) -> JobSubmitResponse:
        data = await self._http.request(
            "POST",
            ROUTES["jobs_submit"],
            json={
                "job_name": job_name,
                "job_type": job_type,
                "payload": payload,
                "resource": resource,
            },
            idempotency_key=idempotency_key,
        )
        return JobSubmitResponse.model_validate(data)

    async def submit_many(
        self,
        jobs: Sequence[JobSubmitRequest | dict[str, Any]],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitMultipleResponse:
        body = {
            "jobs": [
                j.model_dump() if isinstance(j, JobSubmitRequest) else j for j in jobs
            ]
        }
        data = await self._http.request(
            "POST",
            ROUTES["jobs_submit_multiple"],
            json=body,
            idempotency_key=idempotency_key,
        )
        return JobSubmitMultipleResponse.model_validate(data)

    async def list(self) -> ListJobsResponse:
        data = await self._http.request("GET", ROUTES["jobs_list"])
        return ListJobsResponse.model_validate(data)

    async def info(self, process_id: str) -> JobInfoResponse:
        data = await self._http.request(
            "GET", ROUTES["jobs_info"], params={"process_id": process_id}
        )
        return JobInfoResponse.model_validate(data)

    async def status(self, process_id: str) -> ProcessStatus:
        data = await self._http.request(
            "GET", ROUTES["jobs_status"], params={"process_id": process_id}
        )
        return ProcessStatus.model_validate(data)

    async def result(
        self,
        process_id: str,
        *,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        result = await self._http.request(
            "GET",
            ROUTES["jobs_result"],
            params={"process_id": process_id},
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    async def result_many(
        self,
        process_ids: Sequence[str],
        *,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        result = await self._http.request(
            "GET",
            ROUTES["jobs_result_multiple"],
            params={"process_ids": ",".join(process_ids)},
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    async def cancel(self, process_id: str) -> MessageResponse:
        data = await self._http.request(
            "DELETE", ROUTES["jobs_cancel"], params={"process_id": process_id}
        )
        return MessageResponse.model_validate(data)

    async def delete(self, process_id: str) -> MessageResponse:
        data = await self._http.request(
            "DELETE", ROUTES["jobs_delete"], params={"process_id": process_id}
        )
        return MessageResponse.model_validate(data)

    async def wait(
        self,
        process_id: str,
        *,
        poll_interval: float = DEFAULT_JOB_POLL_INTERVAL,
        timeout: float = DEFAULT_JOB_TIMEOUT,
        raise_on_failure: bool = False,
    ) -> ProcessStatus:
        return await await_for_terminal(
            lambda: self.status(process_id),
            poll_interval=poll_interval,
            timeout=timeout,
            terminal_statuses=JOB_TERMINAL_STATUSES,
            raise_on_failure=raise_on_failure,
        )

    async def run(
        self,
        job_name: str,
        job_type: str,
        payload: dict[str, Any],
        *,
        resource: str = "default",
        idempotency_key: str | None = None,
        poll_interval: float = DEFAULT_JOB_POLL_INTERVAL,
        timeout: float = DEFAULT_JOB_TIMEOUT,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        submitted = await self.submit(
            job_name,
            job_type,
            payload,
            resource=resource,
            idempotency_key=idempotency_key,
        )
        await self.wait(
            submitted.process_id,
            poll_interval=poll_interval,
            timeout=timeout,
            raise_on_failure=True,
        )
        return await self.result(submitted.process_id, save_path=save_path)
