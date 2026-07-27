"""Shared polling helpers for long-running processes."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from cognichem_client.constants import POLLABLE_TERMINAL_STATUSES
from cognichem_client.errors import (
    PollTimeoutError,
    ProcessCancelledError,
    ProcessFailedError,
)
from cognichem_client.types import ProcessStatus


def wait_for_terminal(
    status_fn: Callable[[], ProcessStatus],
    *,
    poll_interval: float,
    timeout: float,
    terminal_statuses: frozenset[str] = POLLABLE_TERMINAL_STATUSES,
    raise_on_failure: bool = False,
) -> ProcessStatus:
    """Poll ``status_fn`` until a terminal status or timeout."""
    deadline = time.monotonic() + timeout
    while True:
        status = status_fn()
        if status.status in terminal_statuses:
            if raise_on_failure:
                _raise_if_failed(status)
            return status
        if time.monotonic() >= deadline:
            raise PollTimeoutError(
                f"Timed out after {timeout}s waiting for process "
                f"{status.process_id} (last status={status.status!r})",
                status=None,
            )
        time.sleep(poll_interval)


async def await_for_terminal(
    status_fn: Callable[[], Awaitable[ProcessStatus]],
    *,
    poll_interval: float,
    timeout: float,
    terminal_statuses: frozenset[str] = POLLABLE_TERMINAL_STATUSES,
    raise_on_failure: bool = False,
) -> ProcessStatus:
    """Async variant of :func:`wait_for_terminal`."""
    deadline = time.monotonic() + timeout
    while True:
        status = await status_fn()
        if status.status in terminal_statuses:
            if raise_on_failure:
                _raise_if_failed(status)
            return status
        if time.monotonic() >= deadline:
            raise PollTimeoutError(
                f"Timed out after {timeout}s waiting for process "
                f"{status.process_id} (last status={status.status!r})",
                status=None,
            )
        await asyncio.sleep(poll_interval)


def _raise_if_failed(status: ProcessStatus) -> None:
    if status.status == "error":
        raise ProcessFailedError(
            status.message or f"Process {status.process_id} failed",
            detail=status.message,
        )
    if status.status == "cancelled":
        raise ProcessCancelledError(
            status.message or f"Process {status.process_id} was cancelled",
            detail=status.message,
        )
