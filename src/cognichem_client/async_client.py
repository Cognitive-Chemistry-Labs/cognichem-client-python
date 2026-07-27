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
    """Asynchronous client for the CogniChem compute API (``/api/v1``).

    Parameters
    ----------
    api_key : str or None, optional
        Raw API key secret sent as ``X-Api-Key``. Provide this and/or
        ``access_token``.
    access_token : str or None, optional
        JWT access token sent as ``Authorization: Bearer``.
    base_url : str or None, optional
        API origin. Defaults to ``https://api.cognichem.com``.
    timeout : float, optional
        Default HTTP timeout in seconds.

    Attributes
    ----------
    auth : AsyncAuthResource
        Authentication helpers (login, check, refresh, logout).
    api_keys : AsyncApiKeysResource
        API key CRUD and rotation (JWT required).
    jobs : AsyncJobsResource
        Long-running job submit/poll/result endpoints.
    inference : AsyncInferenceResource
        Inference submit/poll/result and nested MPNN model routes.
    utils : AsyncUtilsResource
        Short-running utility endpoints.
    usage : AsyncUsageResource
        Usage limit queries.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        access_token: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        """Initialize the asynchronous client and resource namespaces.

        Parameters
        ----------
        api_key : str or None, optional
            Raw API key secret sent as ``X-Api-Key``.
        access_token : str or None, optional
            JWT access token sent as ``Authorization: Bearer``.
        base_url : str or None, optional
            API origin. Defaults to production when omitted.
        timeout : float, optional
            Default HTTP timeout in seconds.
        """
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
        """Construct an async client from environment variables.

        Parameters
        ----------
        api_key_var : str, optional
            Environment variable holding the API key.
        access_token_var : str, optional
            Environment variable holding a JWT access token.
        base_url_var : str, optional
            Environment variable holding the API base URL.
        timeout : float, optional
            Default HTTP timeout in seconds.

        Returns
        -------
        AsyncCogniChem
            Configured async client instance.

        Raises
        ------
        ValueError
            If neither API key nor access token is present in the environment.
        """
        return cls(
            api_key=os.environ.get(api_key_var) or None,
            access_token=os.environ.get(access_token_var) or None,
            base_url=os.environ.get(base_url_var) or None,
            timeout=timeout,
        )

    async def aclose(self) -> None:
        """Close the underlying async HTTP client and free connections.

        Returns
        -------
        None
        """
        await self._http.aclose()

    async def __aenter__(self) -> AsyncCogniChem:
        """Enter an async context manager that closes the client on exit.

        Returns
        -------
        AsyncCogniChem
            This client instance.
        """
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit the async context manager and close the client.

        Parameters
        ----------
        *args : object
            Standard context-manager exception info (unused).
        """
        await self.aclose()
