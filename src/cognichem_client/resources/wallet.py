"""Wallet resource clients (``GET /wallet``)."""

from __future__ import annotations

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import WalletBalance


class WalletResource:
    """Synchronous wallet endpoint (``GET /wallet``).

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

    def balance(self) -> WalletBalance:
        """Return the wallet balance and USD held by active reservations.

        Returns
        -------
        WalletBalance
            ``balance`` and ``active_reserved`` in USD.
        """
        data = self._http.request("GET", ROUTES["wallet"])
        return WalletBalance.model_validate(data)


class AsyncWalletResource:
    """Asynchronous wallet endpoint (``GET /wallet``).

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

    async def balance(self) -> WalletBalance:
        """Return the wallet balance and USD held by active reservations.

        Returns
        -------
        WalletBalance
            ``balance`` and ``active_reserved`` in USD.
        """
        data = await self._http.request("GET", ROUTES["wallet"])
        return WalletBalance.model_validate(data)
