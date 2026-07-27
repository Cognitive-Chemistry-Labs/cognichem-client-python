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
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def submit(
        self,
        utility_type: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitResponse:
        data = self._http.request(
            "POST",
            ROUTES["utils_submit"],
            json={"utility_type": utility_type, "payload": payload},
            idempotency_key=idempotency_key,
        )
        return JobSubmitResponse.model_validate(data)

    def list(self) -> ListProcessIdsResponse:
        data = self._http.request("GET", ROUTES["utils_list"])
        return ListProcessIdsResponse.model_validate(data)

    def status(self, process_id: str) -> ProcessStatus:
        data = self._http.request(
            "GET", ROUTES["utils_status"], params={"process_id": process_id}
        )
        return ProcessStatus.model_validate(data)

    def result(self, process_id: str) -> DataResult:
        data = self._http.request(
            "GET", ROUTES["utils_result"], params={"process_id": process_id}
        )
        return DataResult.model_validate(data)

    def delete(self, process_id: str) -> MessageResponse:
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
    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def submit(
        self,
        utility_type: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> JobSubmitResponse:
        data = await self._http.request(
            "POST",
            ROUTES["utils_submit"],
            json={"utility_type": utility_type, "payload": payload},
            idempotency_key=idempotency_key,
        )
        return JobSubmitResponse.model_validate(data)

    async def list(self) -> ListProcessIdsResponse:
        data = await self._http.request("GET", ROUTES["utils_list"])
        return ListProcessIdsResponse.model_validate(data)

    async def status(self, process_id: str) -> ProcessStatus:
        data = await self._http.request(
            "GET", ROUTES["utils_status"], params={"process_id": process_id}
        )
        return ProcessStatus.model_validate(data)

    async def result(self, process_id: str) -> DataResult:
        data = await self._http.request(
            "GET", ROUTES["utils_result"], params={"process_id": process_id}
        )
        return DataResult.model_validate(data)

    async def delete(self, process_id: str) -> MessageResponse:
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
