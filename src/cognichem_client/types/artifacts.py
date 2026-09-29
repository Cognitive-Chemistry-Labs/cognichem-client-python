"""Models for durable artifacts under ``/artifacts``."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ArtifactListItem(BaseModel):
    """One chainable manifest port of an owned artifact.

    Attributes
    ----------
    artifact_id : str
        Artifact identifier (``art-…``); bind it as ``$artifact`` in a
        WorkflowSpec.
    port : str
        Manifest port name (``archive`` only with ``include_archive=True``).
    data_kind : str
        Port data kind (e.g. ``molecule_set``, ``protein_structure``).
    data_format : str
        Port data format (e.g. ``smiles``, ``pdb``).
    record_count : int
        Records on this port.
    size_bytes : int
        Stored size in bytes.
    is_virtual : bool
        Whether the artifact is a view over a parent artifact.
    created_at, expires_at : str or None
        ISO-8601 timestamps.
    job_id, run_id, step_id : str or None
        Producing job, workflow run, and step, when known.
    job_name, job_type, run_name : str or None
        Display labels for the producer.
    """

    artifact_id: str
    port: str
    data_kind: str
    data_format: str
    record_count: int = 0
    size_bytes: int = 0
    is_virtual: bool = False
    created_at: str | None = None
    expires_at: str | None = None
    job_id: str | None = None
    run_id: str | None = None
    step_id: str | None = None
    job_name: str | None = None
    job_type: str | None = None
    run_name: str | None = None


class ArtifactListResponse(BaseModel):
    """Page of artifact ports.

    Paging is over artifacts, not items: every port of one artifact lands on
    the same page.

    Attributes
    ----------
    items : list of ArtifactListItem
        Port rows.
    has_more : bool
        Whether another page may exist.
    next_offset : int or None
        ``offset`` for the next page, when ``has_more``.
    """

    items: list[ArtifactListItem] = Field(default_factory=list)
    has_more: bool = False
    next_offset: int | None = None


class ArtifactUsage(BaseModel):
    """Artifact storage usage against the tier quota.

    Attributes
    ----------
    used_bytes : int
        Bytes stored.
    quota_bytes : int
        Tier quota in bytes.
    artifact_count : int
        Number of stored artifacts.
    tier : int
        Caller subscription tier.
    """

    used_bytes: int
    quota_bytes: int
    artifact_count: int
    tier: int


class Artifact(BaseModel):
    """Owner-visible artifact metadata plus its parsed manifest.

    Attributes
    ----------
    id : str
        Artifact identifier.
    job_id : str or None
        Producing job, when known.
    size_bytes : int
        Stored size in bytes.
    content_type : str
        Media type of the stored object.
    expires_at, created_at : str or None
        ISO-8601 timestamps.
    manifest : dict
        Manifest with ``ports`` → ``records`` (ids, files, metrics). Pass a
        record ``id`` to :meth:`ArtifactsResource.download` as ``record``.
    """

    id: str
    job_id: str | None = None
    size_bytes: int = 0
    content_type: str = "application/octet-stream"
    expires_at: str | None = None
    created_at: str | None = None
    manifest: dict[str, Any] = Field(default_factory=dict)
