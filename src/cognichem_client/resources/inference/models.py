"""Inference model metadata resource clients."""

from __future__ import annotations

from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import MessageResponse


class MpnnModelsResource:
    """MPNN public/user model metadata under ``client.inference.models.mpnn``.

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

    def public(self) -> dict[str, Any]:
        """List publicly available MPNN models.

        Returns
        -------
        dict
            Public model metadata payload (or ``{"data": ...}`` wrapper).
        """
        data = self._http.request("GET", ROUTES["mpnn_public_models"])
        return data if isinstance(data, dict) else {"data": data}

    def user(self, model_name: str | None = None) -> dict[str, Any]:
        """List or fetch the caller's MPNN user models.

        Parameters
        ----------
        model_name : str or None, optional
            When provided, filter to a single model name.

        Returns
        -------
        dict
            User model metadata payload (or ``{"data": ...}`` wrapper).
        """
        params = {"model_name": model_name} if model_name else None
        data = self._http.request(
            "GET", ROUTES["mpnn_user_models"], params=params
        )
        return data if isinstance(data, dict) else {"data": data}

    def delete(self, model_name: str) -> MessageResponse:
        """Delete a named MPNN user model.

        Parameters
        ----------
        model_name : str
            User model name to delete.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = self._http.request(
            "DELETE",
            ROUTES["mpnn_user_models"],
            params={"model_name": model_name},
        )
        return MessageResponse.model_validate(data)


class AsyncMpnnModelsResource:
    """Asynchronous MPNN public/user model metadata client.

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

    async def public(self) -> dict[str, Any]:
        """List publicly available MPNN models.

        Returns
        -------
        dict
            Public model metadata payload (or ``{"data": ...}`` wrapper).
        """
        data = await self._http.request("GET", ROUTES["mpnn_public_models"])
        return data if isinstance(data, dict) else {"data": data}

    async def user(self, model_name: str | None = None) -> dict[str, Any]:
        """List or fetch the caller's MPNN user models.

        Parameters
        ----------
        model_name : str or None, optional
            When provided, filter to a single model name.

        Returns
        -------
        dict
            User model metadata payload (or ``{"data": ...}`` wrapper).
        """
        params = {"model_name": model_name} if model_name else None
        data = await self._http.request(
            "GET", ROUTES["mpnn_user_models"], params=params
        )
        return data if isinstance(data, dict) else {"data": data}

    async def delete(self, model_name: str) -> MessageResponse:
        """Delete a named MPNN user model.

        Parameters
        ----------
        model_name : str
            User model name to delete.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = await self._http.request(
            "DELETE",
            ROUTES["mpnn_user_models"],
            params={"model_name": model_name},
        )
        return MessageResponse.model_validate(data)


class InferenceModels:
    """Namespace for sync inference model-metadata resources.

    Parameters
    ----------
    http : HttpClient
        Shared HTTP transport.

    Attributes
    ----------
    mpnn : MpnnModelsResource
        MPNN public and user model endpoints.
    """

    def __init__(self, http: HttpClient) -> None:
        """Build nested model-metadata resource clients.

        Parameters
        ----------
        http : HttpClient
            Shared HTTP transport.
        """
        self.mpnn = MpnnModelsResource(http)


class AsyncInferenceModels:
    """Namespace for async inference model-metadata resources.

    Parameters
    ----------
    http : AsyncHttpClient
        Shared async HTTP transport.

    Attributes
    ----------
    mpnn : AsyncMpnnModelsResource
        Asynchronous MPNN public and user model endpoints.
    """

    def __init__(self, http: AsyncHttpClient) -> None:
        """Build nested async model-metadata resource clients.

        Parameters
        ----------
        http : AsyncHttpClient
            Shared async HTTP transport.
        """
        self.mpnn = AsyncMpnnModelsResource(http)
