"""Models for the run completion events feed (``GET /events``)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RunEvent(BaseModel):
    """One stop transition of a job or workflow run.

    Events are thin: re-read ``client.jobs.status`` or
    ``client.workflows.runs.get`` for detail.

    Attributes
    ----------
    event_id : int
        Dedupe key (delivery is at-least-once).
    cursor : str
        Opaque cursor positioned at this event.
    kind : str
        ``job`` or ``workflow_run``.
    subject_id : str
        Job process id or workflow run id.
    status : str
        Jobs: ``completed``, ``error``, ``cancelled``. Workflow runs:
        ``completed``, ``failed``, ``cancelled``, ``paused``.
    workflow_run_id : str or None
        Owning run when the job is a workflow step.
    occurred_at : datetime
        When the transition happened.
    """

    event_id: int
    cursor: str
    kind: str
    subject_id: str
    status: str
    workflow_run_id: str | None = None
    occurred_at: datetime


class RunEventList(BaseModel):
    """A page of events after the ``after`` cursor, oldest first.

    Attributes
    ----------
    events : list of RunEvent
        Events in order.
    next_cursor : str or None
        Pass as ``after`` on the next call (unchanged when no events).
    """

    events: list[RunEvent] = Field(default_factory=list)
    next_cursor: str | None = None
