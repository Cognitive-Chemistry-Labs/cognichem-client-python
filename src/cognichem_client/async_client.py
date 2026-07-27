"""Async CogniChem API client facade."""

from __future__ import annotations

import os

from cognichem_client._http import AsyncHttpClient
from cognichem_client.constants import DEFAULT_BASE_URL, DEFAULT_HTTP_TIMEOUT
from cognichem_client.resources.api_keys import AsyncApiKeysResource
from cognichem_client.resources.auth import AsyncAuthResource
from cognichem_client.resources.inference import AsyncInferenceResource
from cognichem_client.resources.jobs import AsyncJobsResource
from cognichem_client.resources.usage import AsyncUsageResource
from cognichem_client.resources.utils import AsyncUtilsResource


class AsyncCogniChem:
    """Asynchronous client for the CogniChem compute API (``/api/v1``)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        access_token: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        self._http = AsyncHttpClient(
            base_url=base_url or DEFAULT_BASE_URL,
            api_key=api_key,
            access_token=access_token,
            timeout=timeout,
        )
        self.auth = AsyncAuthResource(self._http)
        self.api_keys = AsyncApiKeysResource(self._http)
        self.jobs = AsyncJobsResource(self._http)
        self.inference = AsyncInferenceResource(self._http)
        self.utils = AsyncUtilsResource(self._http)
        self.usage = AsyncUsageResource(self._http)

    @classmethod
    def from_env(
        cls,
        *,
        api_key_var: str = "COGNICHEM_API_KEY",
        access_token_var: str = "COGNICHEM_ACCESS_TOKEN",
        base_url_var: str = "COGNICHEM_BASE_URL",
        timeout: float = DEFAULT_HTTP_TIMEOUT,
    ) -> AsyncCogniChem:
        return cls(
            api_key=os.environ.get(api_key_var) or None,
            access_token=os.environ.get(access_token_var) or None,
            base_url=os.environ.get(base_url_var) or None,
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncCogniChem:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()
