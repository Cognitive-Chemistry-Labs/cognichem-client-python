"""Shared polling helpers for long-running processes and workflow runs."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

from cognichem_client.constants import POLLABLE_TERMINAL_STATUSES
from cognichem_client.errors import (
    PollTimeoutError,
    ProcessCancelledError,
    ProcessFailedError,
)
from cognichem_client.types import ProcessStatus


class _HasStatus(Protocol):
    """Anything with a string ``status`` (process status, workflow run)."""

    @property
    def status(self) -> str:
        """Current status string."""
        ...


S = TypeVar("S", bound=_HasStatus)

_PROCESS_FAILED = frozenset({"error"})
_RUN_FAILED = frozenset({"failed"})


def wait_for_terminal(
    status_fn: Callable[[], ProcessStatus],
    *,
    poll_interval: float,
    timeout: float,
    terminal_statuses: frozenset[str] = POLLABLE_TERMINAL_STATUSES,
    raise_on_failure: bool = False,
) -> ProcessStatus:
    """Poll ``status_fn`` until a terminal status or timeout.

    Parameters
    ----------
    status_fn : callable
        Zero-argument callable returning a :class:`ProcessStatus`.
    poll_interval : float
        Seconds to sleep between polls.
    timeout : float
        Maximum seconds to wait before raising :class:`PollTimeoutError`.
    terminal_statuses : frozenset of str, optional
        Status strings treated as terminal.
    raise_on_failure : bool, optional
        When ``True``, raise if the terminal status is ``error`` or
        ``cancelled``.

    Returns
    -------
    ProcessStatus
        Final terminal status payload.

    Raises
    ------
    PollTimeoutError
        If ``timeout`` elapses before a terminal status.
    ProcessFailedError
        If ``raise_on_failure`` is true and status is ``error``.
    ProcessCancelledError
        If ``raise_on_failure`` is true and status is ``cancelled``.
    """
    return poll_until(
        status_fn,
        poll_interval=poll_interval,
        timeout=timeout,
        stop_statuses=terminal_statuses,
        subject=lambda s: f"process {s.process_id}",
        failed_statuses=_PROCESS_FAILED if raise_on_failure else None,
    )


async def await_for_terminal(
    status_fn: Callable[[], Awaitable[ProcessStatus]],
    *,
    poll_interval: float,
    timeout: float,
    terminal_statuses: frozenset[str] = POLLABLE_TERMINAL_STATUSES,
    raise_on_failure: bool = False,
) -> ProcessStatus:
    """Asynchronously poll ``status_fn`` until a terminal status or timeout.

    Parameters
    ----------
    status_fn : callable
        Zero-argument async callable returning a :class:`ProcessStatus`.
    poll_interval : float
        Seconds to sleep between polls.
    timeout : float
        Maximum seconds to wait before raising :class:`PollTimeoutError`.
    terminal_statuses : frozenset of str, optional
        Status strings treated as terminal.
    raise_on_failure : bool, optional
        When ``True``, raise if the terminal status is ``error`` or
        ``cancelled``.

    Returns
    -------
    ProcessStatus
        Final terminal status payload.

    Raises
    ------
    PollTimeoutError
        If ``timeout`` elapses before a terminal status.
    ProcessFailedError
        If ``raise_on_failure`` is true and status is ``error``.
    ProcessCancelledError
        If ``raise_on_failure`` is true and status is ``cancelled``.
    """
    return await apoll_until(
        status_fn,
        poll_interval=poll_interval,
        timeout=timeout,
        stop_statuses=terminal_statuses,
        subject=lambda s: f"process {s.process_id}",
        failed_statuses=_PROCESS_FAILED if raise_on_failure else None,
    )


def poll_until(
    fetch: Callable[[], S],
    *,
    poll_interval: float,
    timeout: float,
    stop_statuses: frozenset[str],
    subject: Callable[[S], str],
    failed_statuses: frozenset[str] | None = None,
) -> S:
    """Poll ``fetch`` until its ``status`` is in ``stop_statuses``.

    Parameters
    ----------
    fetch : callable
        Zero-argument callable returning an object with a ``status``.
    poll_interval : float
        Seconds to sleep between polls.
    timeout : float
        Maximum seconds to wait before raising :class:`PollTimeoutError`.
    stop_statuses : frozenset of str
        Statuses that end the wait.
    subject : callable
        Describes the polled object for error messages.
    failed_statuses : frozenset of str or None, optional
        When set, raise :class:`ProcessFailedError` for these statuses and
        :class:`ProcessCancelledError` for ``cancelled``.

    Returns
    -------
    object
        The last fetched object (its status is in ``stop_statuses``).

    Raises
    ------
    PollTimeoutError
        If ``timeout`` elapses first.
    ProcessFailedError
        If ``failed_statuses`` is set and the final status is in it.
    ProcessCancelledError
        If ``failed_statuses`` is set and the final status is ``cancelled``.
    """
    deadline = time.monotonic() + timeout
    while True:
        current = fetch()
        if current.status in stop_statuses:
            if failed_statuses is not None:
                _raise_if_failed(current, subject(current), failed_statuses)
            return current
        if time.monotonic() >= deadline:
            raise _timeout(timeout, subject(current), current.status)
        time.sleep(poll_interval)


async def apoll_until(
    fetch: Callable[[], Awaitable[S]],
    *,
    poll_interval: float,
    timeout: float,
    stop_statuses: frozenset[str],
    subject: Callable[[S], str],
    failed_statuses: frozenset[str] | None = None,
) -> S:
    """Asynchronously poll ``fetch`` until its ``status`` is in ``stop_statuses``.

    Parameters
    ----------
    fetch : callable
        Zero-argument async callable returning an object with a ``status``.
    poll_interval : float
        Seconds to sleep between polls.
    timeout : float
        Maximum seconds to wait before raising :class:`PollTimeoutError`.
    stop_statuses : frozenset of str
        Statuses that end the wait.
    subject : callable
        Describes the polled object for error messages.
    failed_statuses : frozenset of str or None, optional
        When set, raise :class:`ProcessFailedError` for these statuses and
        :class:`ProcessCancelledError` for ``cancelled``.

    Returns
    -------
    object
        The last fetched object (its status is in ``stop_statuses``).

    Raises
    ------
    PollTimeoutError
        If ``timeout`` elapses first.
    ProcessFailedError
        If ``failed_statuses`` is set and the final status is in it.
    ProcessCancelledError
        If ``failed_statuses`` is set and the final status is ``cancelled``.
    """
    deadline = time.monotonic() + timeout
    while True:
        current = await fetch()
        if current.status in stop_statuses:
            if failed_statuses is not None:
                _raise_if_failed(current, subject(current), failed_statuses)
            return current
        if time.monotonic() >= deadline:
            raise _timeout(timeout, subject(current), current.status)
        await asyncio.sleep(poll_interval)


def run_failure_statuses(raise_on_failure: bool) -> frozenset[str] | None:
    """Return the workflow-run failure set when ``raise_on_failure`` is set.

    Parameters
    ----------
    raise_on_failure : bool
        Whether the caller wants failures raised.

    Returns
    -------
    frozenset of str or None
        ``{"failed"}`` or ``None``.
    """
    return _RUN_FAILED if raise_on_failure else None


def _timeout(timeout: float, subject: str, status: str) -> PollTimeoutError:
    """Build the timeout error raised by the poll loops.

    Parameters
    ----------
    timeout : float
        Configured timeout in seconds.
    subject : str
        Description of the polled object.
    status : str
        Last observed status.

    Returns
    -------
    PollTimeoutError
        Error to raise.
    """
    return PollTimeoutError(
        f"Timed out after {timeout}s waiting for {subject} (last status={status!r})",
        status=None,
    )


def _raise_if_failed(
    current: _HasStatus, subject: str, failed_statuses: frozenset[str]
) -> None:
    """Raise for failed or cancelled final statuses.

    Parameters
    ----------
    current : object
        Final polled object.
    subject : str
        Description of the polled object.
    failed_statuses : frozenset of str
        Statuses that count as failure.

    Raises
    ------
    ProcessFailedError
        When the status is in ``failed_statuses``.
    ProcessCancelledError
        When the status is ``cancelled``.
    """
    message = getattr(current, "message", None) or getattr(
        current, "status_message", None
    )
    label = subject[:1].upper() + subject[1:]
    if current.status in failed_statuses:
        raise ProcessFailedError(
            message or f"{label} failed",
            detail=message,
        )
    if current.status == "cancelled":
        raise ProcessCancelledError(
            message or f"{label} was cancelled",
            detail=message,
        )
