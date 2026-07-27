"""Inference process resource clients under ``/inference``."""

from __future__ import annotations

from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import (
    DEFAULT_FAST_POLL_INTERVAL,
    DEFAULT_FAST_TIMEOUT,
    ROUTES,
)
from cognichem_client.polling import await_for_terminal, wait_for_terminal
from cognichem_client.resources.inference.models import (
    AsyncInferenceModels,
    InferenceModels,
)
from cognichem_client.types import (
    DataResult,
    InferenceSubmitRequest,
    JobSubmitMultipleResponse,
    JobSubmitResponse,
    ListProcessIdsResponse,
    MessageResponse,
    ProcessStatus,
)


class InferenceResource:
    """Synchronous inference endpoints under ``/inference``.

    Parameters
    ----------
    http : HttpClient
        Shared HTTP transport.

    Attributes
    ----------
    models : InferenceModels
        Nested model-metadata resources (e.g. ``.models.mpnn``).
    """

    def __init__(self, http: HttpClient) -> None:
        """Attach the shared HTTP transport and model namespace.

        Parameters
        ----------
        http : HttpClient
            Shared HTTP transport.
        """
        self._http = http
        self.models = InferenceModels(http)

    def submit(
        self,
        model_type: str,
        model_name: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitResponse:
        """Submit a single inference process.

        Parameters
        ----------
        model_type : str
            Model family (see :data:`~cognichem_client.constants.MODEL_TYPES`).
        model_name : str
            Specific model identifier within the family.
        payload : dict
            Model-specific request payload.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitResponse
            Submission acknowledgement including ``process_id``.
        """
        data = self._http.request(
            "POST",
            ROUTES["inference_submit"],
            json={
                "model_type": model_type,
                "model_name": model_name,
                "payload": payload,
            },
            idempotency_key=idempotency_key,
        )
        return JobSubmitResponse.model_validate(data)

    def submit_batch(
        self,
        jobs: list[InferenceSubmitRequest | dict[str, Any]],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitMultipleResponse:
        """Submit multiple inference processes in one request.

        Parameters
        ----------
        jobs : list of InferenceSubmitRequest or dict
            Inference specifications to submit.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitMultipleResponse
            Per-job submission acknowledgements.
        """
        body = {
            "jobs": [
                j.model_dump() if isinstance(j, InferenceSubmitRequest) else j
                for j in jobs
            ]
        }
        data = self._http.request(
            "POST",
            ROUTES["inference_submit_batch"],
            json=body,
            idempotency_key=idempotency_key,
        )
        return JobSubmitMultipleResponse.model_validate(data)

    def list(self) -> ListProcessIdsResponse:
        """List process IDs for the caller's inference runs.

        Returns
        -------
        ListProcessIdsResponse
            Collection of inference process identifiers.
        """
        data = self._http.request("GET", ROUTES["inference_list"])
        return ListProcessIdsResponse.model_validate(data)

    def status(self, process_id: str) -> ProcessStatus:
        """Fetch the current status of an inference process.

        Parameters
        ----------
        process_id : str
            Inference process identifier.

        Returns
        -------
        ProcessStatus
            Latest status payload.
        """
        data = self._http.request(
            "GET", ROUTES["inference_status"], params={"process_id": process_id}
        )
        return ProcessStatus.model_validate(data)

    def result(self, process_id: str) -> DataResult:
        """Fetch the JSON result of a completed inference process.

        Parameters
        ----------
        process_id : str
            Inference process identifier.

        Returns
        -------
        DataResult
            Structured result payload.
        """
        data = self._http.request(
            "GET", ROUTES["inference_result"], params={"process_id": process_id}
        )
        return DataResult.model_validate(data)

    def delete(self, process_id: str) -> MessageResponse:
        """Delete an inference process and its stored artifacts.

        Parameters
        ----------
        process_id : str
            Inference process identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = self._http.request(
            "DELETE",
            ROUTES["inference_delete"],
            params={"process_id": process_id},
        )
        return MessageResponse.model_validate(data)

    def wait(
        self,
        process_id: str,
        *,
        poll_interval: float = DEFAULT_FAST_POLL_INTERVAL,
        timeout: float = DEFAULT_FAST_TIMEOUT,
        raise_on_failure: bool = False,
    ) -> ProcessStatus:
        """Poll until the inference process reaches a terminal status.

        Parameters
        ----------
        process_id : str
            Inference process identifier.
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
            raise_on_failure=raise_on_failure,
        )

    def run(
        self,
        model_type: str,
        model_name: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        poll_interval: float = DEFAULT_FAST_POLL_INTERVAL,
        timeout: float = DEFAULT_FAST_TIMEOUT,
    ) -> DataResult:
        """Submit inference, wait for completion, and return its result.

        Parameters
        ----------
        model_type : str
            Model family (see :data:`~cognichem_client.constants.MODEL_TYPES`).
        model_name : str
            Specific model identifier within the family.
        payload : dict
            Model-specific request payload.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.
        poll_interval : float, optional
            Seconds between status polls.
        timeout : float, optional
            Maximum seconds to wait before raising
            :class:`~cognichem_client.errors.PollTimeoutError`.

        Returns
        -------
        DataResult
            Structured result from the completed process.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses before a terminal status.
        ProcessFailedError
            If the process terminates with status ``error``.
        ProcessCancelledError
            If the process terminates with status ``cancelled``.
        """
        submitted = self.submit(
            model_type,
            model_name,
            payload,
            idempotency_key=idempotency_key,
        )
        self.wait(
            submitted.process_id,
            poll_interval=poll_interval,
            timeout=timeout,
            raise_on_failure=True,
        )
        return self.result(submitted.process_id)


class AsyncInferenceResource:
    """Asynchronous inference endpoints under ``/inference``.

    Parameters
    ----------
    http : AsyncHttpClient
        Shared async HTTP transport.

    Attributes
    ----------
    models : AsyncInferenceModels
        Nested async model-metadata resources (e.g. ``.models.mpnn``).
    """

    def __init__(self, http: AsyncHttpClient) -> None:
        """Attach the shared async HTTP transport and model namespace.

        Parameters
        ----------
        http : AsyncHttpClient
            Shared async HTTP transport.
        """
        self._http = http
        self.models = AsyncInferenceModels(http)

    async def submit(
        self,
        model_type: str,
        model_name: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitResponse:
        """Submit a single inference process.

        Parameters
        ----------
        model_type : str
            Model family (see :data:`~cognichem_client.constants.MODEL_TYPES`).
        model_name : str
            Specific model identifier within the family.
        payload : dict
            Model-specific request payload.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitResponse
            Submission acknowledgement including ``process_id``.
        """
        data = await self._http.request(
            "POST",
            ROUTES["inference_submit"],
            json={
                "model_type": model_type,
                "model_name": model_name,
                "payload": payload,
            },
            idempotency_key=idempotency_key,
        )
        return JobSubmitResponse.model_validate(data)

    async def submit_batch(
        self,
        jobs: list[InferenceSubmitRequest | dict[str, Any]],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitMultipleResponse:
        """Submit multiple inference processes in one request.

        Parameters
        ----------
        jobs : list of InferenceSubmitRequest or dict
            Inference specifications to submit.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitMultipleResponse
            Per-job submission acknowledgements.
        """
        body = {
            "jobs": [
                j.model_dump() if isinstance(j, InferenceSubmitRequest) else j
                for j in jobs
            ]
        }
        data = await self._http.request(
            "POST",
            ROUTES["inference_submit_batch"],
            json=body,
            idempotency_key=idempotency_key,
        )
        return JobSubmitMultipleResponse.model_validate(data)

    async def list(self) -> ListProcessIdsResponse:
        """List process IDs for the caller's inference runs.

        Returns
        -------
        ListProcessIdsResponse
            Collection of inference process identifiers.
        """
        data = await self._http.request("GET", ROUTES["inference_list"])
        return ListProcessIdsResponse.model_validate(data)

    async def status(self, process_id: str) -> ProcessStatus:
        """Fetch the current status of an inference process.

        Parameters
        ----------
        process_id : str
            Inference process identifier.

        Returns
        -------
        ProcessStatus
            Latest status payload.
        """
        data = await self._http.request(
            "GET", ROUTES["inference_status"], params={"process_id": process_id}
        )
        return ProcessStatus.model_validate(data)

    async def result(self, process_id: str) -> DataResult:
        """Fetch the JSON result of a completed inference process.

        Parameters
        ----------
        process_id : str
            Inference process identifier.

        Returns
        -------
        DataResult
            Structured result payload.
        """
        data = await self._http.request(
            "GET", ROUTES["inference_result"], params={"process_id": process_id}
        )
        return DataResult.model_validate(data)

    async def delete(self, process_id: str) -> MessageResponse:
        """Delete an inference process and its stored artifacts.

        Parameters
        ----------
        process_id : str
            Inference process identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = await self._http.request(
            "DELETE",
            ROUTES["inference_delete"],
            params={"process_id": process_id},
        )
        return MessageResponse.model_validate(data)

    async def wait(
        self,
        process_id: str,
        *,
        poll_interval: float = DEFAULT_FAST_POLL_INTERVAL,
        timeout: float = DEFAULT_FAST_TIMEOUT,
        raise_on_failure: bool = False,
    ) -> ProcessStatus:
        """Poll until the inference process reaches a terminal status.

        Parameters
        ----------
        process_id : str
            Inference process identifier.
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
            raise_on_failure=raise_on_failure,
        )

    async def run(
        self,
        model_type: str,
        model_name: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        poll_interval: float = DEFAULT_FAST_POLL_INTERVAL,
        timeout: float = DEFAULT_FAST_TIMEOUT,
    ) -> DataResult:
        """Submit inference, wait for completion, and return its result.

        Parameters
        ----------
        model_type : str
            Model family (see :data:`~cognichem_client.constants.MODEL_TYPES`).
        model_name : str
            Specific model identifier within the family.
        payload : dict
            Model-specific request payload.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.
        poll_interval : float, optional
            Seconds between status polls.
        timeout : float, optional
            Maximum seconds to wait before raising
            :class:`~cognichem_client.errors.PollTimeoutError`.

        Returns
        -------
        DataResult
            Structured result from the completed process.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses before a terminal status.
        ProcessFailedError
            If the process terminates with status ``error``.
        ProcessCancelledError
            If the process terminates with status ``cancelled``.
        """
        submitted = await self.submit(
            model_type,
            model_name,
            payload,
            idempotency_key=idempotency_key,
        )
        await self.wait(
            submitted.process_id,
            poll_interval=poll_interval,
            timeout=timeout,
            raise_on_failure=True,
        )
        return await self.result(submitted.process_id)


__all__ = ["AsyncInferenceResource", "InferenceResource"]
