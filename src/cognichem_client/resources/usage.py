from __future__ import annotations

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import UsageLimitsResponse


class UsageResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def limits(self, month: str | None = None) -> UsageLimitsResponse:
        params = {"month": month} if month else None
        data = self._http.request("GET", ROUTES["usage_limits"], params=params)
        return UsageLimitsResponse.model_validate(data)


class AsyncUsageResource:
    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def limits(self, month: str | None = None) -> UsageLimitsResponse:
        params = {"month": month} if month else None
        data = await self._http.request("GET", ROUTES["usage_limits"], params=params)
        return UsageLimitsResponse.model_validate(data)
