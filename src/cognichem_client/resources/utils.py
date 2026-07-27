"""Utility process resource clients under ``/utils``."""

from __future__ import annotations

from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import (
    DEFAULT_FAST_POLL_INTERVAL,
    DEFAULT_FAST_TIMEOUT,
    ROUTES,
)
from cognichem_client.polling import await_for_terminal, wait_for_terminal
from cognichem_client.types import (
    DataResult,
    JobSubmitResponse,
    ListProcessIdsResponse,
    MessageResponse,
    ProcessStatus,
)


class UtilsResource:
    """Synchronous utility-process endpoints under ``/utils``.

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
        utility_type: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitResponse:
        """Submit a utility process for asynchronous execution.

        Parameters
        ----------
        utility_type : str
            Utility catalog type (e.g. ``convert``, ``molecule_rmsd``).
        payload : dict
            Type-specific request payload.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitResponse
            Submission acknowledgement including ``process_id``.
        """
        data = self._http.request(
            "POST",
            ROUTES["utils_submit"],
            json={"utility_type": utility_type, "payload": payload},
            idempotency_key=idempotency_key,
        )
        return JobSubmitResponse.model_validate(data)

    def list(self) -> ListProcessIdsResponse:
        """List process IDs for the caller's utility runs.

        Returns
        -------
        ListProcessIdsResponse
            Collection of utility process identifiers.
        """
        data = self._http.request("GET", ROUTES["utils_list"])
        return ListProcessIdsResponse.model_validate(data)

    def status(self, process_id: str) -> ProcessStatus:
        """Fetch the current status of a utility process.

        Parameters
        ----------
        process_id : str
            Utility process identifier.

        Returns
        -------
        ProcessStatus
            Latest status payload.
        """
        data = self._http.request(
            "GET", ROUTES["utils_status"], params={"process_id": process_id}
        )
        return ProcessStatus.model_validate(data)

    def result(self, process_id: str) -> DataResult:
        """Fetch the JSON result of a completed utility process.

        Parameters
        ----------
        process_id : str
            Utility process identifier.

        Returns
        -------
        DataResult
            Structured result payload.
        """
        data = self._http.request(
            "GET", ROUTES["utils_result"], params={"process_id": process_id}
        )
        return DataResult.model_validate(data)

    def delete(self, process_id: str) -> MessageResponse:
        """Delete a utility process and its stored artifacts.

        Parameters
        ----------
        process_id : str
            Utility process identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = self._http.request(
            "DELETE", ROUTES["utils_delete"], params={"process_id": process_id}
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
        """Poll until the utility process reaches a terminal status.

        Parameters
        ----------
        process_id : str
            Utility process identifier.
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
        utility_type: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        poll_interval: float = DEFAULT_FAST_POLL_INTERVAL,
        timeout: float = DEFAULT_FAST_TIMEOUT,
    ) -> DataResult:
        """Submit a utility, wait for completion, and return its result.

        Parameters
        ----------
        utility_type : str
            Utility catalog type (e.g. ``convert``, ``molecule_rmsd``).
        payload : dict
            Type-specific request payload.
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
            utility_type, payload, idempotency_key=idempotency_key
        )
        self.wait(
            submitted.process_id,
            poll_interval=poll_interval,
            timeout=timeout,
            raise_on_failure=True,
        )
        return self.result(submitted.process_id)


class AsyncUtilsResource:
    """Asynchronous utility-process endpoints under ``/utils``.

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
        utility_type: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitResponse:
        """Submit a utility process for asynchronous execution.

        Parameters
        ----------
        utility_type : str
            Utility catalog type (e.g. ``convert``, ``molecule_rmsd``).
        payload : dict
            Type-specific request payload.
        idempotency_key : str or None, optional
            Optional idempotency key for safe retries.

        Returns
        -------
        JobSubmitResponse
            Submission acknowledgement including ``process_id``.
        """
        data = await self._http.request(
            "POST",
            ROUTES["utils_submit"],
            json={"utility_type": utility_type, "payload": payload},
            idempotency_key=idempotency_key,
        )
        return JobSubmitResponse.model_validate(data)

    async def list(self) -> ListProcessIdsResponse:
        """List process IDs for the caller's utility runs.

        Returns
        -------
        ListProcessIdsResponse
            Collection of utility process identifiers.
        """
        data = await self._http.request("GET", ROUTES["utils_list"])
        return ListProcessIdsResponse.model_validate(data)

    async def status(self, process_id: str) -> ProcessStatus:
        """Fetch the current status of a utility process.

        Parameters
        ----------
        process_id : str
            Utility process identifier.

        Returns
        -------
        ProcessStatus
            Latest status payload.
        """
        data = await self._http.request(
            "GET", ROUTES["utils_status"], params={"process_id": process_id}
        )
        return ProcessStatus.model_validate(data)

    async def result(self, process_id: str) -> DataResult:
        """Fetch the JSON result of a completed utility process.

        Parameters
        ----------
        process_id : str
            Utility process identifier.

        Returns
        -------
        DataResult
            Structured result payload.
        """
        data = await self._http.request(
            "GET", ROUTES["utils_result"], params={"process_id": process_id}
        )
        return DataResult.model_validate(data)

    async def delete(self, process_id: str) -> MessageResponse:
        """Delete a utility process and its stored artifacts.

        Parameters
        ----------
        process_id : str
            Utility process identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = await self._http.request(
            "DELETE", ROUTES["utils_delete"], params={"process_id": process_id}
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
        """Poll until the utility process reaches a terminal status.

        Parameters
        ----------
        process_id : str
            Utility process identifier.
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
        utility_type: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
        poll_interval: float = DEFAULT_FAST_POLL_INTERVAL,
        timeout: float = DEFAULT_FAST_TIMEOUT,
    ) -> DataResult:
        """Submit a utility, wait for completion, and return its result.

        Parameters
        ----------
        utility_type : str
            Utility catalog type (e.g. ``convert``, ``molecule_rmsd``).
        payload : dict
            Type-specific request payload.
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
            utility_type, payload, idempotency_key=idempotency_key
        )
        await self.wait(
            submitted.process_id,
            poll_interval=poll_interval,
            timeout=timeout,
            raise_on_failure=True,
        )
        return await self.result(submitted.process_id)
