"""API key management resource clients."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import (
    ApiKeyCreatedResponse,
    ApiKeyListItem,
    ApiKeyListResponse,
)


def _create_body(
    name: str,
    *,
    scopes: Sequence[str] | None,
    expires_at: datetime | str | None,
    spend_ceiling_usd: float | None,
    allow_structure_search: bool,
) -> dict[str, Any]:
    """Build the ``POST /auth/api-keys`` body, omitting unset options.

    Parameters
    ----------
    name : str
        Display name.
    scopes : sequence of str or None
        Scopes (subset of ``read``, ``write``).
    expires_at : datetime or str or None
        Expiry instant.
    spend_ceiling_usd : float or None
        Per-key USD cap.
    allow_structure_search : bool
        ChEMBL structure-search opt-in.

    Returns
    -------
    dict
        JSON body.
    """
    body: dict[str, Any] = {"name": name}
    if scopes is not None:
        body["scopes"] = list(scopes)
    if expires_at is not None:
        body["expires_at"] = (
            expires_at.isoformat() if isinstance(expires_at, datetime) else expires_at
        )
    if spend_ceiling_usd is not None:
        body["spend_ceiling_usd"] = spend_ceiling_usd
    if allow_structure_search:
        body["allow_structure_search"] = True
    return body


def _update_body(
    name: str | None, allow_structure_search: bool | None
) -> dict[str, Any]:
    """Build the ``PATCH /auth/api-keys/{key_id}`` body.

    Parameters
    ----------
    name : str or None
        New display name.
    allow_structure_search : bool or None
        New structure-search opt-in.

    Returns
    -------
    dict
        JSON body with only the fields to change.

    Raises
    ------
    ValueError
        If neither field is given.
    """
    body: dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if allow_structure_search is not None:
        body["allow_structure_search"] = allow_structure_search
    if not body:
        raise ValueError("Provide name and/or allow_structure_search")
    return body


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
        data = self._http.request("GET", ROUTES["auth_api_keys"], prefer_bearer=True)
        return ApiKeyListResponse.model_validate(data)

    def create(
        self,
        name: str,
        *,
        scopes: Sequence[str] | None = None,
        expires_at: datetime | str | None = None,
        spend_ceiling_usd: float | None = None,
        allow_structure_search: bool = False,
    ) -> ApiKeyCreatedResponse:
        """Create a named API key.

        Parameters
        ----------
        name : str
            Display name (unique per user, 1-64 characters).
        scopes : sequence of str or None, optional
            Subset of ``read`` and ``write`` (default both). Submitting jobs
            or workflow runs needs ``write``.
        expires_at : datetime or str or None, optional
            Instant after which the key is rejected.
        spend_ceiling_usd : float or None, optional
            Per-key USD spend cap (``None`` means wallet-only).
        allow_structure_search : bool, optional
            Let this key send SMILES to ChEMBL similarity / substructure
            search via ``/lookup/chembl`` (off by default).

        Returns
        -------
        ApiKeyCreatedResponse
            Metadata plus the raw secret (returned once).
        """
        data = self._http.request(
            "POST",
            ROUTES["auth_api_keys"],
            json=_create_body(
                name,
                scopes=scopes,
                expires_at=expires_at,
                spend_ceiling_usd=spend_ceiling_usd,
                allow_structure_search=allow_structure_search,
            ),
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

    def update(
        self,
        key_id: str,
        *,
        name: str | None = None,
        allow_structure_search: bool | None = None,
    ) -> ApiKeyListItem:
        """Rename an API key and/or change its structure-search opt-in.

        Parameters
        ----------
        key_id : str
            Credential UUID.
        name : str or None, optional
            New display name.
        allow_structure_search : bool or None, optional
            Let the key send SMILES to ChEMBL similarity / substructure
            search.

        Returns
        -------
        ApiKeyListItem
            Updated key metadata.

        Raises
        ------
        ValueError
            If neither ``name`` nor ``allow_structure_search`` is given.
        """
        data = self._http.request(
            "PATCH",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            json=_update_body(name, allow_structure_search),
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    def rename(self, key_id: str, name: str) -> ApiKeyListItem:
        """Rename an API key (shorthand for :meth:`update`).

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
        return self.update(key_id, name=name)

    def delete(self, key_id: str) -> None:
        """Revoke an API key.

        Parameters
        ----------
        key_id : str
            Credential UUID.

        Returns
        -------
        None
            The API answers 204 No Content.
        """
        self._http.request(
            "DELETE",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )

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

    async def create(
        self,
        name: str,
        *,
        scopes: Sequence[str] | None = None,
        expires_at: datetime | str | None = None,
        spend_ceiling_usd: float | None = None,
        allow_structure_search: bool = False,
    ) -> ApiKeyCreatedResponse:
        """Create a named API key.

        Parameters
        ----------
        name : str
            Display name (unique per user, 1-64 characters).
        scopes : sequence of str or None, optional
            Subset of ``read`` and ``write`` (default both). Submitting jobs
            or workflow runs needs ``write``.
        expires_at : datetime or str or None, optional
            Instant after which the key is rejected.
        spend_ceiling_usd : float or None, optional
            Per-key USD spend cap (``None`` means wallet-only).
        allow_structure_search : bool, optional
            Let this key send SMILES to ChEMBL similarity / substructure
            search via ``/lookup/chembl`` (off by default).

        Returns
        -------
        ApiKeyCreatedResponse
            Metadata plus the raw secret (returned once).
        """
        data = await self._http.request(
            "POST",
            ROUTES["auth_api_keys"],
            json=_create_body(
                name,
                scopes=scopes,
                expires_at=expires_at,
                spend_ceiling_usd=spend_ceiling_usd,
                allow_structure_search=allow_structure_search,
            ),
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

    async def update(
        self,
        key_id: str,
        *,
        name: str | None = None,
        allow_structure_search: bool | None = None,
    ) -> ApiKeyListItem:
        """Rename an API key and/or change its structure-search opt-in.

        Parameters
        ----------
        key_id : str
            Credential UUID.
        name : str or None, optional
            New display name.
        allow_structure_search : bool or None, optional
            Let the key send SMILES to ChEMBL similarity / substructure
            search.

        Returns
        -------
        ApiKeyListItem
            Updated key metadata.

        Raises
        ------
        ValueError
            If neither ``name`` nor ``allow_structure_search`` is given.
        """
        data = await self._http.request(
            "PATCH",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            json=_update_body(name, allow_structure_search),
            prefer_bearer=True,
        )
        return ApiKeyListItem.model_validate(data)

    async def rename(self, key_id: str, name: str) -> ApiKeyListItem:
        """Rename an API key (shorthand for :meth:`update`).

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
        return await self.update(key_id, name=name)

    async def delete(self, key_id: str) -> None:
        """Revoke an API key.

        Parameters
        ----------
        key_id : str
            Credential UUID.

        Returns
        -------
        None
            The API answers 204 No Content.
        """
        await self._http.request(
            "DELETE",
            ROUTES["auth_api_keys_item"].format(key_id=key_id),
            prefer_bearer=True,
        )

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
