"""API key management resource clients."""

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
    """Synchronous API key management under ``/auth/api-keys``.

    These routes require JWT (Bearer). An API key alone is not sufficient.

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

    def list(self) -> ApiKeyListResponse:
        """List API keys and tier capacity metadata.

        Returns
        -------
        ApiKeyListResponse
            Keys, limit, and count.
        """
        data = self._http.request(
            "GET", ROUTES["auth_api_keys"], prefer_bearer=True
        )
        return ApiKeyListResponse.model_validate(data)

    def create(self, name: str) -> ApiKeyCreatedResponse:
        """Create a named API key.

        Parameters
        ----------
        name : str
            Display name (unique per user).

        Returns
        -------
        ApiKeyCreatedResponse
            Metadata plus the raw secret (returned once).
        """
        data = self._http.request(
            "POST",
            ROUTES["auth_api_keys"],
            json={"name": name},
            prefer_bearer=True,
        )
        return ApiKeyCreatedResponse.model_validate(data)

    def get(self, key_id: str) -> ApiKeyListItem:
        """Fetch metadata for one API key.

        Parameters
        ----------
        key_id : str
            Credential UUID.

        Returns
        -------
        ApiKeyListItem
            Key metadata (no secret).
        """
        data = self._http.request(
            "GET",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    def rename(self, key_id: str, name: str) -> ApiKeyListItem:
        """Rename an API key.

        Parameters
        ----------
        key_id : str
            Credential UUID.
        name : str
            New display name.

        Returns
        -------
        ApiKeyListItem
            Updated key metadata.
        """
        data = self._http.request(
            "PATCH",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            json={"name": name},
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    def delete(self, key_id: str) -> MessageResponse:
        """Revoke (hard-delete) an API key.

        Parameters
        ----------
        key_id : str
            Credential UUID.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = self._http.request(
            "DELETE",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return MessageResponse.model_validate(data)

    def rotate(self, key_id: str) -> ApiKeyCreatedResponse:
        """Rotate an API key and return the new secret once.

        Parameters
        ----------
        key_id : str
            Credential UUID.

        Returns
        -------
        ApiKeyCreatedResponse
            Updated metadata plus the new raw secret.
        """
        data = self._http.request(
            "POST",
            ROUTES["auth_api_keys_rotate"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return ApiKeyCreatedResponse.model_validate(data)


class AsyncApiKeysResource:
    """Asynchronous API key management under ``/auth/api-keys``.

    These routes require JWT (Bearer). An API key alone is not sufficient.

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

    async def list(self) -> ApiKeyListResponse:
        """List API keys and tier capacity metadata.

        Returns
        -------
        ApiKeyListResponse
            Keys, limit, and count.
        """
        data = await self._http.request(
            "GET", ROUTES["auth_api_keys"], prefer_bearer=True
        )
        return ApiKeyListResponse.model_validate(data)

    async def create(self, name: str) -> ApiKeyCreatedResponse:
        """Create a named API key.

        Parameters
        ----------
        name : str
            Display name (unique per user).

        Returns
        -------
        ApiKeyCreatedResponse
            Metadata plus the raw secret (returned once).
        """
        data = await self._http.request(
            "POST",
            ROUTES["auth_api_keys"],
            json={"name": name},
            prefer_bearer=True,
        )
        return ApiKeyCreatedResponse.model_validate(data)

    async def get(self, key_id: str) -> ApiKeyListItem:
        """Fetch metadata for one API key.

        Parameters
        ----------
        key_id : str
            Credential UUID.

        Returns
        -------
        ApiKeyListItem
            Key metadata (no secret).
        """
        data = await self._http.request(
            "GET",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    async def rename(self, key_id: str, name: str) -> ApiKeyListItem:
        """Rename an API key.

        Parameters
        ----------
        key_id : str
            Credential UUID.
        name : str
            New display name.

        Returns
        -------
        ApiKeyListItem
            Updated key metadata.
        """
        data = await self._http.request(
            "PATCH",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            json={"name": name},
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    async def delete(self, key_id: str) -> MessageResponse:
        """Revoke (hard-delete) an API key.

        Parameters
        ----------
        key_id : str
            Credential UUID.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = await self._http.request(
            "DELETE",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return MessageResponse.model_validate(data)

    async def rotate(self, key_id: str) -> ApiKeyCreatedResponse:
        """Rotate an API key and return the new secret once.

        Parameters
        ----------
        key_id : str
            Credential UUID.

        Returns
        -------
        ApiKeyCreatedResponse
            Updated metadata plus the new raw secret.
        """
        data = await self._http.request(
            "POST",
            ROUTES["auth_api_keys_rotate"].format(key_id=key_id),
            prefer_bearer=True,
        )
        return ApiKeyCreatedResponse.model_validate(data)
