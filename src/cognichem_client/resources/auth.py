"""Authentication resource clients."""

from __future__ import annotations

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import AuthCheckResponse, MessageResponse, TokenResponse


class AuthResource:
    """Synchronous authentication endpoints under ``/auth``.

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

    def login_email(
        self, email: str, password: str, *, store_token: bool = True
    ) -> TokenResponse:
        """Authenticate with email/password (OAuth2 password form).

        When ``store_token`` is true, the access token is stored on the client
        so subsequent calls (e.g. API key management) can use Bearer auth.

        Parameters
        ----------
        email : str
            Account email (sent as OAuth2 ``username``).
        password : str
            Account password.
        store_token : bool, optional
            Persist the returned access token on the HTTP client.

        Returns
        -------
        TokenResponse
            Access and refresh tokens.
        """
        data = self._http.request(
            "POST",
            ROUTES["auth_login_email"],
            data={"username": email, "password": password},
            content_type="application/x-www-form-urlencoded",
        )
        tokens = TokenResponse.model_validate(data)
        if store_token:
            self._http.use_access_token(tokens.access_token)
        return tokens

    def check(self) -> AuthCheckResponse:
        """Verify that the current credentials are accepted.

        Returns
        -------
        AuthCheckResponse
            Confirmation payload from ``GET /auth/check``.
        """
        data = self._http.request("GET", ROUTES["auth_check"])
        return AuthCheckResponse.model_validate(data or {})

    def refresh(self, refresh_token: str, *, store_token: bool = True) -> TokenResponse:
        """Exchange a refresh token for a new access token.

        Parameters
        ----------
        refresh_token : str
            Refresh token from a prior login.
        store_token : bool, optional
            Persist the new access token on the HTTP client.

        Returns
        -------
        TokenResponse
            New token pair.
        """
        data = self._http.request(
            "GET",
            ROUTES["auth_refresh"],
            params={"refresh_token": refresh_token},
        )
        tokens = TokenResponse.model_validate(data)
        if store_token:
            self._http.use_access_token(tokens.access_token)
        return tokens

    def logout(self) -> MessageResponse:
        """Invalidate the current JWT session.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = self._http.request(
            "GET",
            ROUTES["auth_logout"],
            prefer_bearer=True,
        )
        return MessageResponse.model_validate(data)


class AsyncAuthResource:
    """Asynchronous authentication endpoints under ``/auth``.

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

    async def login_email(
        self, email: str, password: str, *, store_token: bool = True
    ) -> TokenResponse:
        """Authenticate with email/password (OAuth2 password form).

        Parameters
        ----------
        email : str
            Account email (sent as OAuth2 ``username``).
        password : str
            Account password.
        store_token : bool, optional
            Persist the returned access token on the HTTP client.

        Returns
        -------
        TokenResponse
            Access and refresh tokens.
        """
        data = await self._http.request(
            "POST",
            ROUTES["auth_login_email"],
            data={"username": email, "password": password},
            content_type="application/x-www-form-urlencoded",
        )
        tokens = TokenResponse.model_validate(data)
        if store_token:
            self._http.use_access_token(tokens.access_token)
        return tokens

    async def check(self) -> AuthCheckResponse:
        """Verify that the current credentials are accepted.

        Returns
        -------
        AuthCheckResponse
            Confirmation payload from ``GET /auth/check``.
        """
        data = await self._http.request("GET", ROUTES["auth_check"])
        return AuthCheckResponse.model_validate(data or {})

    async def refresh(
        self, refresh_token: str, *, store_token: bool = True
    ) -> TokenResponse:
        """Exchange a refresh token for a new access token.

        Parameters
        ----------
        refresh_token : str
            Refresh token from a prior login.
        store_token : bool, optional
            Persist the new access token on the HTTP client.

        Returns
        -------
        TokenResponse
            New token pair.
        """
        data = await self._http.request(
            "GET",
            ROUTES["auth_refresh"],
            params={"refresh_token": refresh_token},
        )
        tokens = TokenResponse.model_validate(data)
        if store_token:
            self._http.use_access_token(tokens.access_token)
        return tokens

    async def logout(self) -> MessageResponse:
        """Invalidate the current JWT session.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = await self._http.request(
            "GET",
            ROUTES["auth_logout"],
            prefer_bearer=True,
        )
        return MessageResponse.model_validate(data)
