from __future__ import annotations

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import AuthCheckResponse, MessageResponse, TokenResponse


class AuthResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def login_email(
        self, email: str, password: str, *, store_token: bool = True
    ) -> TokenResponse:
        """Authenticate with email/password (OAuth2 password form).

        When ``store_token`` is true, the access token is stored on the client so
        subsequent calls (e.g. API key management) can use Bearer auth.
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
        data = self._http.request("GET", ROUTES["auth_check"])
        return AuthCheckResponse.model_validate(data or {})

    def refresh(self, refresh_token: str, *, store_token: bool = True) -> TokenResponse:
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
        data = self._http.request(
            "GET",
            ROUTES["auth_logout"],
            prefer_bearer=True,
        )
        return MessageResponse.model_validate(data)


class AsyncAuthResource:
    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def login_email(
        self, email: str, password: str, *, store_token: bool = True
    ) -> TokenResponse:
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
        data = await self._http.request("GET", ROUTES["auth_check"])
        return AuthCheckResponse.model_validate(data or {})

    async def refresh(
        self, refresh_token: str, *, store_token: bool = True
    ) -> TokenResponse:
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
        data = await self._http.request(
            "GET",
            ROUTES["auth_logout"],
            prefer_bearer=True,
        )
        return MessageResponse.model_validate(data)
