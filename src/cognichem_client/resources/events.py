"""Run completion events resource clients (``GET /events``)."""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator, Iterator
from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import MAX_EVENTS_WAIT, ROUTES, EventKind
from cognichem_client.types import RunEvent, RunEventList

# Recent event ids remembered by ``listen`` to drop at-least-once repeats.
_DEDUPE_WINDOW = 1000


def _params(
    *,
    after: str | None,
    kind: EventKind | None,
    subject_id: str | None,
    limit: int,
    wait: float,
) -> dict[str, Any]:
    """Build ``GET /events`` query parameters, dropping unset values.

    Parameters
    ----------
    after : str or None
        Cursor.
    kind : str or None
        Subject kind filter.
    subject_id : str or None
        Subject filter.
    limit : int
        Page size.
    wait : float
        Long-poll seconds.

    Returns
    -------
    dict
        Query parameters.
    """
    params: dict[str, Any] = {"limit": limit}
    if wait:
        params["wait"] = wait
    for key, value in (("after", after), ("kind", kind), ("subject_id", subject_id)):
        if value is not None:
            params[key] = value
    return params


class _Deduper:
    """Bounded memory of seen ``event_id`` values."""

    def __init__(self) -> None:
        """Start with no seen ids."""
        self._order: deque[int] = deque()
        self._seen: set[int] = set()

    def first_time(self, event_id: int) -> bool:
        """Record ``event_id`` and report whether it is new.

        Parameters
        ----------
        event_id : int
            Event dedupe key.

        Returns
        -------
        bool
            ``True`` the first time an id is seen.
        """
        if event_id in self._seen:
            return False
        self._seen.add(event_id)
        self._order.append(event_id)
        if len(self._order) > _DEDUPE_WINDOW:
            self._seen.discard(self._order.popleft())
        return True


class EventsResource:
    """Synchronous run completion events feed.

    Each event is one stop transition of a job or workflow run, retained for
    7 days. Delivery is at-least-once and gap-free; dedupe on ``event_id``.

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

    def list(
        self,
        *,
        after: str | None = None,
        kind: EventKind | None = None,
        subject_id: str | None = None,
        limit: int = 50,
        wait: float = 0,
    ) -> RunEventList:
        """Fetch one page of events after a cursor, oldest first.

        Parameters
        ----------
        after : str or None, optional
            ``next_cursor`` from a previous page; omit for the oldest
            retained event.
        kind : {"job", "workflow_run"} or None, optional
            Keep only one subject kind.
        subject_id : str or None, optional
            Keep only events for one job or run.
        limit : int, optional
            Page size (1-100).
        wait : float, optional
            Seconds (up to 25) to hold the request open when there are no
            events yet.

        Returns
        -------
        RunEventList
            Events and ``next_cursor``.
        """
        data = self._http.request(
            "GET",
            ROUTES["events"],
            params=_params(
                after=after, kind=kind, subject_id=subject_id, limit=limit, wait=wait
            ),
        )
        return RunEventList.model_validate(data)

    def listen(
        self,
        *,
        after: str | None = None,
        kind: EventKind | None = None,
        subject_id: str | None = None,
        wait: float = MAX_EVENTS_WAIT,
    ) -> Iterator[RunEvent]:
        """Yield events forever, long-polling and following the cursor.

        Repeats from at-least-once delivery are dropped. Stop by breaking out
        of the loop.

        Parameters
        ----------
        after : str or None, optional
            Cursor to start after; omit for the oldest retained event.
        kind : {"job", "workflow_run"} or None, optional
            Keep only one subject kind.
        subject_id : str or None, optional
            Keep only events for one job or run.
        wait : float, optional
            Long-poll seconds per request (up to 25).

        Yields
        ------
        RunEvent
            Events in order.
        """
        seen = _Deduper()
        cursor = after
        while True:
            page = self.list(after=cursor, kind=kind, subject_id=subject_id, wait=wait)
            for event in page.events:
                if seen.first_time(event.event_id):
                    yield event
            if page.next_cursor:
                cursor = page.next_cursor


class AsyncEventsResource:
    """Asynchronous run completion events feed.

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

    async def list(
        self,
        *,
        after: str | None = None,
        kind: EventKind | None = None,
        subject_id: str | None = None,
        limit: int = 50,
        wait: float = 0,
    ) -> RunEventList:
        """Fetch one page of events after a cursor, oldest first.

        Parameters
        ----------
        after : str or None, optional
            ``next_cursor`` from a previous page.
        kind : {"job", "workflow_run"} or None, optional
            Keep only one subject kind.
        subject_id : str or None, optional
            Keep only events for one job or run.
        limit : int, optional
            Page size (1-100).
        wait : float, optional
            Seconds (up to 25) to hold the request open when there are no
            events yet.

        Returns
        -------
        RunEventList
            Events and ``next_cursor``.
        """
        data = await self._http.request(
            "GET",
            ROUTES["events"],
            params=_params(
                after=after, kind=kind, subject_id=subject_id, limit=limit, wait=wait
            ),
        )
        return RunEventList.model_validate(data)

    async def listen(
        self,
        *,
        after: str | None = None,
        kind: EventKind | None = None,
        subject_id: str | None = None,
        wait: float = MAX_EVENTS_WAIT,
    ) -> AsyncIterator[RunEvent]:
        """Yield events forever, long-polling and following the cursor.

        Parameters
        ----------
        after : str or None, optional
            Cursor to start after.
        kind : {"job", "workflow_run"} or None, optional
            Keep only one subject kind.
        subject_id : str or None, optional
            Keep only events for one job or run.
        wait : float, optional
            Long-poll seconds per request (up to 25).

        Yields
        ------
        RunEvent
            Events in order, without repeats.
        """
        seen = _Deduper()
        cursor = after
        while True:
            page = await self.list(
                after=cursor, kind=kind, subject_id=subject_id, wait=wait
            )
            for event in page.events:
                if seen.first_time(event.event_id):
                    yield event
            if page.next_cursor:
                cursor = page.next_cursor
