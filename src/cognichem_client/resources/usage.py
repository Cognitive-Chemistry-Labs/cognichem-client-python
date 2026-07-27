"""Usage-limits resource clients."""

from __future__ import annotations

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import UsageLimitsResponse


class UsageResource:
    """Synchronous usage-limit endpoints.

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

    def limits(self, month: str | None = None) -> UsageLimitsResponse:
        """Retrieve usage statistics and monthly limits.

        Parameters
        ----------
        month : str or None, optional
            Month in ``YYYY-MM`` form. Defaults to the current month when
            omitted.

        Returns
        -------
        UsageLimitsResponse
            Usage/limit payload from ``GET /usage-limits``.
        """
        params = {"month": month} if month else None
        data = self._http.request("GET", ROUTES["usage_limits"], params=params)
        return UsageLimitsResponse.model_validate(data)


class AsyncUsageResource:
    """Asynchronous usage-limit endpoints.

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

    async def limits(self, month: str | None = None) -> UsageLimitsResponse:
        """Retrieve usage statistics and monthly limits.

        Parameters
        ----------
        month : str or None, optional
            Month in ``YYYY-MM`` form. Defaults to the current month when
            omitted.

        Returns
        -------
        UsageLimitsResponse
            Usage/limit payload from ``GET /usage-limits``.
        """
        params = {"month": month} if month else None
        data = await self._http.request("GET", ROUTES["usage_limits"], params=params)
        return UsageLimitsResponse.model_validate(data)
