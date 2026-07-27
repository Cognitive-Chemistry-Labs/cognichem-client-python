"""Shared HTTP transport for sync and async CogniChem clients."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import httpx

from cognichem_client.constants import DEFAULT_BASE_URL, DEFAULT_HTTP_TIMEOUT
from cognichem_client.errors import raise_for_problem
from cognichem_client.types import BinaryResult

_FILENAME_RE = re.compile(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', re.IGNORECASE)


def _parse_filename(content_disposition: str | None) -> str | None:
    if not content_disposition:
        return None
    match = _FILENAME_RE.search(content_disposition)
    if not match:
        return None
    return match.group(1).strip()


class _BaseHttp:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        access_token: str | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        if not api_key and not access_token:
            raise ValueError("Provide api_key or access_token")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.access_token = access_token
        self.timeout = timeout

    def _headers(
        self,
        *,
        idempotency_key: str | None = None,
        content_type: str | None = "application/json",
        prefer_bearer: bool = False,
    ) -> dict[str, str]:
        headers: dict[str, str] = {}
        if content_type:
            headers["Content-Type"] = content_type
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        # Backend prefers X-Api-Key when both are present. Use Bearer-only when
        # prefer_bearer is set (API key management requires JWT).
        if prefer_bearer and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.api_key:
            headers["X-Api-Key"] = self.api_key
        elif self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def use_access_token(self, access_token: str) -> None:
        self.access_token = access_token

    def use_api_key(self, api_key: str) -> None:
        self.api_key = api_key

    @staticmethod
    def _raise_if_error(response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            body: Any = response.json()
        except Exception:
            body = response.text
        raise_for_problem(
            response.status_code,
            body,
            fallback_message=f"HTTP {response.status_code}",
        )

    @staticmethod
    def _binary_result(response: httpx.Response) -> BinaryResult:
        return BinaryResult(
            content=response.content,
            filename=_parse_filename(response.headers.get("Content-Disposition")),
            media_type=response.headers.get("Content-Type"),
        )


class HttpClient(_BaseHttp):
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        access_token: str | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            access_token=access_token,
            timeout=timeout,
        )
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        idempotency_key: str | None = None,
        content_type: str | None = "application/json",
        prefer_bearer: bool = False,
        expect_json: bool = True,
    ) -> Any:
        response = self._client.request(
            method,
            self.url(path),
            params=params,
            json=json,
            data=data,
            headers=self._headers(
                idempotency_key=idempotency_key,
                content_type=content_type,
                prefer_bearer=prefer_bearer,
            ),
        )
        self._raise_if_error(response)
        if response.status_code == 204 or not response.content:
            return None
        if expect_json:
            return response.json()
        return self._binary_result(response)


class AsyncHttpClient(_BaseHttp):
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        access_token: str | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            access_token=access_token,
            timeout=timeout,
        )
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncHttpClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        idempotency_key: str | None = None,
        content_type: str | None = "application/json",
        prefer_bearer: bool = False,
        expect_json: bool = True,
    ) -> Any:
        response = await self._client.request(
            method,
            self.url(path),
            params=params,
            json=json,
            data=data,
            headers=self._headers(
                idempotency_key=idempotency_key,
                content_type=content_type,
                prefer_bearer=prefer_bearer,
            ),
        )
        self._raise_if_error(response)
        if response.status_code == 204 or not response.content:
            return None
        if expect_json:
            return response.json()
        return self._binary_result(response)
