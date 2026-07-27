from __future__ import annotations

from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import MessageResponse


class MpnnModelsResource:
    """MPNN public/user model metadata under ``client.inference.models.mpnn``."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def public(self) -> dict[str, Any]:
        data = self._http.request("GET", ROUTES["mpnn_public_models"])
        return data if isinstance(data, dict) else {"data": data}

    def user(self, model_name: str | None = None) -> dict[str, Any]:
        params = {"model_name": model_name} if model_name else None
        data = self._http.request(
            "GET", ROUTES["mpnn_user_models"], params=params
        )
        return data if isinstance(data, dict) else {"data": data}

    def delete(self, model_name: str) -> MessageResponse:
        data = self._http.request(
            "DELETE",
            ROUTES["mpnn_user_models"],
            params={"model_name": model_name},
        )
        return MessageResponse.model_validate(data)


class AsyncMpnnModelsResource:
    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def public(self) -> dict[str, Any]:
        data = await self._http.request("GET", ROUTES["mpnn_public_models"])
        return data if isinstance(data, dict) else {"data": data}

    async def user(self, model_name: str | None = None) -> dict[str, Any]:
        params = {"model_name": model_name} if model_name else None
        data = await self._http.request(
            "GET", ROUTES["mpnn_user_models"], params=params
        )
        return data if isinstance(data, dict) else {"data": data}

    async def delete(self, model_name: str) -> MessageResponse:
        data = await self._http.request(
            "DELETE",
            ROUTES["mpnn_user_models"],
            params={"model_name": model_name},
        )
        return MessageResponse.model_validate(data)


class InferenceModels:
    def __init__(self, http: HttpClient) -> None:
        self.mpnn = MpnnModelsResource(http)


class AsyncInferenceModels:
    def __init__(self, http: AsyncHttpClient) -> None:
        self.mpnn = AsyncMpnnModelsResource(http)
