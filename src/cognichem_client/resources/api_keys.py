from __future__ import annotations

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import (
    ApiKeyCreatedResponse,
    ApiKeyListItem,
    ApiKeyListResponse,
    MessageResponse,
)


class ApiKeysResource:
    """API key management. Requires JWT (Bearer); API keys alone are insufficient."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self) -> ApiKeyListResponse:
        data = self._http.request(
            "GET", ROUTES["auth_api_keys"], prefer_bearer=True
        )
        return ApiKeyListResponse.model_validate(data)

    def create(self, name: str) -> ApiKeyCreatedResponse:
        data = self._http.request(
            "POST",
            ROUTES["auth_api_keys"],
            json={"name": name},
            prefer_bearer=True,
        )
        return ApiKeyCreatedResponse.model_validate(data)

    def get(self, key_id: str) -> ApiKeyListItem:
        data = self._http.request(
            "GET",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    def rename(self, key_id: str, name: str) -> ApiKeyListItem:
        data = self._http.request(
            "PATCH",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            json={"name": name},
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    def delete(self, key_id: str) -> MessageResponse:
        data = self._http.request(
            "DELETE",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return MessageResponse.model_validate(data)

    def rotate(self, key_id: str) -> ApiKeyCreatedResponse:
        data = self._http.request(
            "POST",
            ROUTES["auth_api_keys_rotate"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return ApiKeyCreatedResponse.model_validate(data)


class AsyncApiKeysResource:
    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def list(self) -> ApiKeyListResponse:
        data = await self._http.request(
            "GET", ROUTES["auth_api_keys"], prefer_bearer=True
        )
        return ApiKeyListResponse.model_validate(data)

    async def create(self, name: str) -> ApiKeyCreatedResponse:
        data = await self._http.request(
            "POST",
            ROUTES["auth_api_keys"],
            json={"name": name},
            prefer_bearer=True,
        )
        return ApiKeyCreatedResponse.model_validate(data)

    async def get(self, key_id: str) -> ApiKeyListItem:
        data = await self._http.request(
            "GET",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    async def rename(self, key_id: str, name: str) -> ApiKeyListItem:
        data = await self._http.request(
            "PATCH",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            json={"name": name},
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    async def delete(self, key_id: str) -> MessageResponse:
        data = await self._http.request(
            "DELETE",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return MessageResponse.model_validate(data)

    async def rotate(self, key_id: str) -> ApiKeyCreatedResponse:
        data = await self._http.request(
            "POST",
            ROUTES["auth_api_keys_rotate"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return ApiKeyCreatedResponse.model_validate(data)
