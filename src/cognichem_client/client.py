"""Sync CogniChem API client facade."""

from __future__ import annotations

import os

from cognichem_client._http import HttpClient
from cognichem_client.constants import DEFAULT_BASE_URL, DEFAULT_HTTP_TIMEOUT
from cognichem_client.resources.api_keys import ApiKeysResource
from cognichem_client.resources.auth import AuthResource
from cognichem_client.resources.inference import InferenceResource
from cognichem_client.resources.jobs import JobsResource
from cognichem_client.resources.usage import UsageResource
from cognichem_client.resources.utils import UtilsResource


class CogniChem:
    """Synchronous client for the CogniChem compute API (``/api/v1``)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        access_token: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        self._http = HttpClient(
            base_url=base_url or DEFAULT_BASE_URL,
            api_key=api_key,
            access_token=access_token,
            timeout=timeout,
        )
        self.auth = AuthResource(self._http)
        self.api_keys = ApiKeysResource(self._http)
        self.jobs = JobsResource(self._http)
        self.inference = InferenceResource(self._http)
        self.utils = UtilsResource(self._http)
        self.usage = UsageResource(self._http)

    @classmethod
    def from_env(
        cls,
        *,
        api_key_var: str = "COGNICHEM_API_KEY",
        access_token_var: str = "COGNICHEM_ACCESS_TOKEN",
        base_url_var: str = "COGNICHEM_BASE_URL",
        timeout: float = DEFAULT_HTTP_TIMEOUT,
    ) -> CogniChem:
        """Construct a client from environment variables."""
        return cls(
            api_key=os.environ.get(api_key_var) or None,
            access_token=os.environ.get(access_token_var) or None,
            base_url=os.environ.get(base_url_var) or None,
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> CogniChem:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
