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
    """Parse a filename from a ``Content-Disposition`` header.

    Parameters
    ----------
    content_disposition : str or None
        Raw header value, if present.

    Returns
    -------
    str or None
        Extracted filename, or ``None`` if not found.
    """
    if not content_disposition:
        return None
    match = _FILENAME_RE.search(content_disposition)
    if not match:
        return None
    return match.group(1).strip()


class _BaseHttp:
    """Shared configuration and header helpers for HTTP clients.

    Parameters
    ----------
    base_url : str, optional
        API origin without a trailing slash requirement.
    api_key : str or None, optional
        API key secret for ``X-Api-Key`` authentication.
    access_token : str or None, optional
        JWT for ``Authorization: Bearer`` authentication.
    timeout : float, optional
        Default request timeout in seconds.

    Raises
    ------
    ValueError
        If neither ``api_key`` nor ``access_token`` is provided.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        access_token: str | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
    ) -> None:
        """Validate credentials and store transport settings.

        Parameters
        ----------
        base_url : str, optional
            API origin.
        api_key : str or None, optional
            API key secret.
        access_token : str or None, optional
            JWT access token.
        timeout : float, optional
            Default request timeout in seconds.

        Raises
        ------
        ValueError
            If neither ``api_key`` nor ``access_token`` is provided.
        """
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
        """Build request headers for the next call.

        Parameters
        ----------
        idempotency_key : str or None, optional
            Optional ``Idempotency-Key`` for mutating POSTs.
        content_type : str or None, optional
            ``Content-Type`` header value, or ``None`` to omit it.
        prefer_bearer : bool, optional
            When ``True`` and an access token is available, send Bearer auth
            only (needed for JWT-only routes such as API key management).

        Returns
        -------
        dict of str to str
            Headers to pass to httpx.
        """
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
        """Join ``base_url`` with an API path.

        Parameters
        ----------
        path : str
            Absolute path under the API origin (e.g. ``/api/v1/jobs/submit``).

        Returns
        -------
        str
            Absolute request URL.
        """
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def use_access_token(self, access_token: str) -> None:
        """Store a JWT access token for subsequent requests.

        Parameters
        ----------
        access_token : str
            Bearer token value.
        """
        self.access_token = access_token

    def use_api_key(self, api_key: str) -> None:
        """Store an API key for subsequent requests.

        Parameters
        ----------
        api_key : str
            Raw API key secret.
        """
        self.api_key = api_key

    @staticmethod
    def _raise_if_error(response: httpx.Response) -> None:
        """Raise a typed client error for non-success HTTP responses.

        Parameters
        ----------
        response : httpx.Response
            Completed HTTP response.

        Raises
        ------
        CogniChemError
            When ``response.is_success`` is false.
        """
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
        """Wrap a binary HTTP response as a :class:`BinaryResult`.

        Parameters
        ----------
        response : httpx.Response
            Successful response with binary content.

        Returns
        -------
        BinaryResult
            Content bytes plus optional filename and media type.
        """
        return BinaryResult(
            content=response.content,
            filename=_parse_filename(response.headers.get("Content-Disposition")),
            media_type=response.headers.get("Content-Type"),
        )


class HttpClient(_BaseHttp):
    """Synchronous httpx transport used by resource classes.

    Parameters
    ----------
    base_url : str, optional
        API origin.
    api_key : str or None, optional
        API key secret.
    access_token : str or None, optional
        JWT access token.
    timeout : float, optional
        Default request timeout in seconds.
    client : httpx.Client or None, optional
        Optional preconfigured httpx client. When omitted, this class owns
        and closes its own client.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        access_token: str | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
        client: httpx.Client | None = None,
    ) -> None:
        """Create or adopt a synchronous httpx client.

        Parameters
        ----------
        base_url : str, optional
            API origin.
        api_key : str or None, optional
            API key secret.
        access_token : str or None, optional
            JWT access token.
        timeout : float, optional
            Default request timeout in seconds.
        client : httpx.Client or None, optional
            Optional preconfigured httpx client.
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            access_token=access_token,
            timeout=timeout,
        )
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        """Close the owned httpx client, if any.

        Returns
        -------
        None
        """
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> HttpClient:
        """Enter a context manager that closes the client on exit.

        Returns
        -------
        HttpClient
            This transport instance.
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
        """Send an HTTP request and return JSON or binary content.

        Parameters
        ----------
        method : str
            HTTP method (``GET``, ``POST``, ``DELETE``, …).
        path : str
            API path under the configured base URL.
        params : dict or None, optional
            Query string parameters.
        json : any, optional
            JSON body (encoded by httpx).
        data : any, optional
            Form or raw body (e.g. OAuth2 password form).
        idempotency_key : str or None, optional
            Optional ``Idempotency-Key`` header.
        content_type : str or None, optional
            ``Content-Type`` header value.
        prefer_bearer : bool, optional
            Prefer Bearer auth over API key when both are available.
        expect_json : bool, optional
            When ``True``, parse and return JSON. When ``False``, return a
            :class:`BinaryResult`.

        Returns
        -------
        any
            Parsed JSON, ``None`` for empty bodies, or :class:`BinaryResult`.

        Raises
        ------
        CogniChemError
            On non-success HTTP responses.
        """
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
    """Asynchronous httpx transport used by async resource classes.

    Parameters
    ----------
    base_url : str, optional
        API origin.
    api_key : str or None, optional
        API key secret.
    access_token : str or None, optional
        JWT access token.
    timeout : float, optional
        Default request timeout in seconds.
    client : httpx.AsyncClient or None, optional
        Optional preconfigured async httpx client.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        access_token: str | None = None,
        timeout: float = DEFAULT_HTTP_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create or adopt an asynchronous httpx client.

        Parameters
        ----------
        base_url : str, optional
            API origin.
        api_key : str or None, optional
            API key secret.
        access_token : str or None, optional
            JWT access token.
        timeout : float, optional
            Default request timeout in seconds.
        client : httpx.AsyncClient or None, optional
            Optional preconfigured async httpx client.
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            access_token=access_token,
            timeout=timeout,
        )
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        """Close the owned async httpx client, if any.

        Returns
        -------
        None
        """
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncHttpClient:
        """Enter an async context manager that closes the client on exit.

        Returns
        -------
        AsyncHttpClient
            This transport instance.
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
        """Send an async HTTP request and return JSON or binary content.

        Parameters
        ----------
        method : str
            HTTP method (``GET``, ``POST``, ``DELETE``, …).
        path : str
            API path under the configured base URL.
        params : dict or None, optional
            Query string parameters.
        json : any, optional
            JSON body (encoded by httpx).
        data : any, optional
            Form or raw body.
        idempotency_key : str or None, optional
            Optional ``Idempotency-Key`` header.
        content_type : str or None, optional
            ``Content-Type`` header value.
        prefer_bearer : bool, optional
            Prefer Bearer auth over API key when both are available.
        expect_json : bool, optional
            When ``True``, parse and return JSON. When ``False``, return a
            :class:`BinaryResult`.

        Returns
        -------
        any
            Parsed JSON, ``None`` for empty bodies, or :class:`BinaryResult`.

        Raises
        ------
        CogniChemError
            On non-success HTTP responses.
        """
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
