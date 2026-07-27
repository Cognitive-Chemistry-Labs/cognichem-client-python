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
    """Synchronous client for the CogniChem compute API (``/api/v1``).

    Parameters
    ----------
    api_key : str or None, optional
        Raw API key secret sent as ``X-Api-Key``. Provide this and/or
        ``access_token``.
    access_token : str or None, optional
        JWT access token sent as ``Authorization: Bearer``. Required for
        API key management routes when no API key should take precedence.
    base_url : str or None, optional
        API origin. Defaults to ``https://api.cognichem.com``.
    timeout : float, optional
        Default HTTP timeout in seconds.

    Attributes
    ----------
    auth : AuthResource
        Authentication helpers (login, check, refresh, logout).
    api_keys : ApiKeysResource
        API key CRUD and rotation (JWT required).
    jobs : JobsResource
        Long-running job submit/poll/result endpoints.
    inference : InferenceResource
        Inference submit/poll/result and nested MPNN model routes.
    utils : UtilsResource
        Short-running utility endpoints.
    usage : UsageResource
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
        """Initialize the synchronous client and resource namespaces.

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
        """Construct a client from environment variables.

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
        CogniChem
            Configured client instance.

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

    def close(self) -> None:
        """Close the underlying HTTP client and free connections.

        Returns
        -------
        None
        """
        self._http.close()

    def __enter__(self) -> CogniChem:
        """Enter a context manager that closes the client on exit.

        Returns
        -------
        CogniChem
            This client instance.
        """
        return self

    def __exit__(self, *args: object) -> None:
        """Exit the context manager and close the client.

        Parameters
        ----------
        *args : object
            Standard context-manager exception info (unused).
        """
        self.close()
