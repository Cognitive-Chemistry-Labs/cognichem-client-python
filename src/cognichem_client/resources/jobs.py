"""Long-running job resource clients under ``/jobs``."""

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
    """Optionally write binary job bytes to disk.

    Parameters
    ----------
    result : BinaryResult
        Binary payload returned by a job result endpoint.
    save_path : str or Path or None
        Destination file path, directory (filename taken from
        ``result.filename``), or ``None`` to skip writing.

    Returns
    -------
    BinaryResult
        The same ``result`` instance (unchanged).
    """
    if save_path is None:
        return result
    path = Path(save_path)
    if path.is_dir():
        filename = result.filename or "result.bin"
        path = path / filename
    path.write_bytes(result.content)
    return result


class JobsResource:
    """Synchronous long-running job endpoints under ``/jobs``.

    Parameters
    ----------
    http : HttpClient
        Shared HTTP transport.
    """

    def __init__(self, http: HttpClient) -> None:
        """Attach the shared HTTP transport.

        Parameters
        ----------
        http : HttpClient
            Shared HTTP transport.
        """
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
        """Submit a single compute job.

        Parameters
        ----------
        job_name : str
            Caller-chosen display name for the job.
        job_type : str
            Catalog job type (see :data:`~cognichem_client.constants.JOB_TYPES`).
        payload : dict
            Type-specific request payload.
        resource : str, optional
            Compute resource tier (default ``default``).
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitResponse
            Submission acknowledgement including ``process_id``.
        """
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
        """Submit multiple compute jobs in one request.

        Parameters
        ----------
        jobs : sequence of JobSubmitRequest or dict
            Job specifications to submit.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitMultipleResponse
            Per-job submission acknowledgements.
        """
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
        """List jobs belonging to the authenticated caller.

        Returns
        -------
        ListJobsResponse
            Job summaries for the current account.
        """
        data = self._http.request("GET", ROUTES["jobs_list"])
        return ListJobsResponse.model_validate(data)

    def info(self, process_id: str) -> JobInfoResponse:
        """Fetch detailed metadata for a job.

        Parameters
        ----------
        process_id : str
            Job process identifier.

        Returns
        -------
        JobInfoResponse
            Detailed job information payload.
        """
        data = self._http.request(
            "GET", ROUTES["jobs_info"], params={"process_id": process_id}
        )
        return JobInfoResponse.model_validate(data)

    def status(self, process_id: str) -> ProcessStatus:
        """Fetch the current status of a job.

        Parameters
        ----------
        process_id : str
            Job process identifier.

        Returns
        -------
        ProcessStatus
            Latest status payload.
        """
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
        """Download the binary result of a completed job.

        Parameters
        ----------
        process_id : str
            Job process identifier.
        save_path : str or Path or None, optional
            Optional file or directory path to write the bytes.

        Returns
        -------
        BinaryResult
            Binary content and optional filename metadata.
        """
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
        """Download a combined binary archive for multiple jobs.

        Parameters
        ----------
        process_ids : sequence of str
            Job process identifiers to include.
        save_path : str or Path or None, optional
            Optional file or directory path to write the bytes.

        Returns
        -------
        BinaryResult
            Combined binary content and optional filename metadata.
        """
        result = self._http.request(
            "GET",
            ROUTES["jobs_result_multiple"],
            params={"process_ids": ",".join(process_ids)},
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    def cancel(self, process_id: str) -> MessageResponse:
        """Request cancellation of a running or queued job.

        Parameters
        ----------
        process_id : str
            Job process identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = self._http.request(
            "DELETE", ROUTES["jobs_cancel"], params={"process_id": process_id}
        )
        return MessageResponse.model_validate(data)

    def delete(self, process_id: str) -> MessageResponse:
        """Delete a job and its stored artifacts.

        Parameters
        ----------
        process_id : str
            Job process identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
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
        """Poll until the job reaches a terminal status.

        Parameters
        ----------
        process_id : str
            Job process identifier.
        poll_interval : float, optional
            Seconds between status polls.
        timeout : float, optional
            Maximum seconds to wait before raising
            :class:`~cognichem_client.errors.PollTimeoutError`.
        raise_on_failure : bool, optional
            When ``True``, raise if the terminal status is ``error`` or
            ``cancelled``.

        Returns
        -------
        ProcessStatus
            Final terminal status payload.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses before a terminal status.
        ProcessFailedError
            If ``raise_on_failure`` is true and status is ``error``.
        ProcessCancelledError
            If ``raise_on_failure`` is true and status is ``cancelled``.
        """
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
        """Submit a job, wait for completion, and download its result.

        Parameters
        ----------
        job_name : str
            Caller-chosen display name for the job.
        job_type : str
            Catalog job type (see :data:`~cognichem_client.constants.JOB_TYPES`).
        payload : dict
            Type-specific request payload.
        resource : str, optional
            Compute resource tier (default ``default``).
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.
        poll_interval : float, optional
            Seconds between status polls.
        timeout : float, optional
            Maximum seconds to wait before raising
            :class:`~cognichem_client.errors.PollTimeoutError`.
        save_path : str or Path or None, optional
            Optional file or directory path to write the result bytes.

        Returns
        -------
        BinaryResult
            Binary content from the completed job.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses before a terminal status.
        ProcessFailedError
            If the job terminates with status ``error``.
        ProcessCancelledError
            If the job terminates with status ``cancelled``.
        """
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
    """Asynchronous long-running job endpoints under ``/jobs``.

    Parameters
    ----------
    http : AsyncHttpClient
        Shared async HTTP transport.
    """

    def __init__(self, http: AsyncHttpClient) -> None:
        """Attach the shared async HTTP transport.

        Parameters
        ----------
        http : AsyncHttpClient
            Shared async HTTP transport.
        """
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
        """Submit a single compute job.

        Parameters
        ----------
        job_name : str
            Caller-chosen display name for the job.
        job_type : str
            Catalog job type (see :data:`~cognichem_client.constants.JOB_TYPES`).
        payload : dict
            Type-specific request payload.
        resource : str, optional
            Compute resource tier (default ``default``).
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitResponse
            Submission acknowledgement including ``process_id``.
        """
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
        """Submit multiple compute jobs in one request.

        Parameters
        ----------
        jobs : sequence of JobSubmitRequest or dict
            Job specifications to submit.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitMultipleResponse
            Per-job submission acknowledgements.
        """
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
        """List jobs belonging to the authenticated caller.

        Returns
        -------
        ListJobsResponse
            Job summaries for the current account.
        """
        data = await self._http.request("GET", ROUTES["jobs_list"])
        return ListJobsResponse.model_validate(data)

    async def info(self, process_id: str) -> JobInfoResponse:
        """Fetch detailed metadata for a job.

        Parameters
        ----------
        process_id : str
            Job process identifier.

        Returns
        -------
        JobInfoResponse
            Detailed job information payload.
        """
        data = await self._http.request(
            "GET", ROUTES["jobs_info"], params={"process_id": process_id}
        )
        return JobInfoResponse.model_validate(data)

    async def status(self, process_id: str) -> ProcessStatus:
        """Fetch the current status of a job.

        Parameters
        ----------
        process_id : str
            Job process identifier.

        Returns
        -------
        ProcessStatus
            Latest status payload.
        """
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
        """Download the binary result of a completed job.

        Parameters
        ----------
        process_id : str
            Job process identifier.
        save_path : str or Path or None, optional
            Optional file or directory path to write the bytes.

        Returns
        -------
        BinaryResult
            Binary content and optional filename metadata.
        """
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
        """Download a combined binary archive for multiple jobs.

        Parameters
        ----------
        process_ids : sequence of str
            Job process identifiers to include.
        save_path : str or Path or None, optional
            Optional file or directory path to write the bytes.

        Returns
        -------
        BinaryResult
            Combined binary content and optional filename metadata.
        """
        result = await self._http.request(
            "GET",
            ROUTES["jobs_result_multiple"],
            params={"process_ids": ",".join(process_ids)},
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    async def cancel(self, process_id: str) -> MessageResponse:
        """Request cancellation of a running or queued job.

        Parameters
        ----------
        process_id : str
            Job process identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = await self._http.request(
            "DELETE", ROUTES["jobs_cancel"], params={"process_id": process_id}
        )
        return MessageResponse.model_validate(data)

    async def delete(self, process_id: str) -> MessageResponse:
        """Delete a job and its stored artifacts.

        Parameters
        ----------
        process_id : str
            Job process identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
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
        """Poll until the job reaches a terminal status.

        Parameters
        ----------
        process_id : str
            Job process identifier.
        poll_interval : float, optional
            Seconds between status polls.
        timeout : float, optional
            Maximum seconds to wait before raising
            :class:`~cognichem_client.errors.PollTimeoutError`.
        raise_on_failure : bool, optional
            When ``True``, raise if the terminal status is ``error`` or
            ``cancelled``.

        Returns
        -------
        ProcessStatus
            Final terminal status payload.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses before a terminal status.
        ProcessFailedError
            If ``raise_on_failure`` is true and status is ``error``.
        ProcessCancelledError
            If ``raise_on_failure`` is true and status is ``cancelled``.
        """
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
        """Submit a job, wait for completion, and download its result.

        Parameters
        ----------
        job_name : str
            Caller-chosen display name for the job.
        job_type : str
            Catalog job type (see :data:`~cognichem_client.constants.JOB_TYPES`).
        payload : dict
            Type-specific request payload.
        resource : str, optional
            Compute resource tier (default ``default``).
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.
        poll_interval : float, optional
            Seconds between status polls.
        timeout : float, optional
            Maximum seconds to wait before raising
            :class:`~cognichem_client.errors.PollTimeoutError`.
        save_path : str or Path or None, optional
            Optional file or directory path to write the result bytes.

        Returns
        -------
        BinaryResult
            Binary content from the completed job.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses before a terminal status.
        ProcessFailedError
            If the job terminates with status ``error``.
        ProcessCancelledError
            If the job terminates with status ``cancelled``.
        """
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
