"""Pydantic models for CogniChem API request/response envelopes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    """Authentication token payload returned by login/refresh.

    Attributes
    ----------
    access_token : str
        JWT access token.
    refresh_token : str
        Refresh token used to obtain a new access token.
    token_type : str
        Token type (typically ``bearer``).
    expires_in : int
        Access-token lifetime in seconds.
    expires_at : int
        Access-token expiration as a UNIX timestamp.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: int


class ApiKeyListItem(BaseModel):
    """API key metadata without the raw secret.

    Attributes
    ----------
    id : str
        Credential row UUID.
    name : str
        User-defined display name (unique per user).
    key_prefix : str or None
        Non-secret prefix for display.
    scopes : list of str
        Reserved scopes (not enforced yet).
    created_at : datetime
        Creation timestamp.
    last_used_at : datetime or None
        Last successful authentication time, if any.
    rotated_at : datetime or None
        Last rotation time, if any.
    """

    id: str
    name: str
    key_prefix: str | None = None
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime
    last_used_at: datetime | None = None
    rotated_at: datetime | None = None


class ApiKeyListResponse(BaseModel):
    """Collection of API keys with tier cap metadata.

    Attributes
    ----------
    keys : list of ApiKeyListItem
        Owned keys (no secrets).
    limit : int
        Maximum keys allowed for the user's subscription tier.
    count : int
        Current number of keys.
    """

    keys: list[ApiKeyListItem]
    limit: int
    count: int


class ApiKeyCreatedResponse(ApiKeyListItem):
    """API key metadata plus the raw secret (create/rotate only).

    Attributes
    ----------
    api_key : str
        Raw secret returned once; list/get never include it.
    """

    api_key: str


class JobSubmitRequest(BaseModel):
    """Job submission envelope.

    Attributes
    ----------
    job_name : str
        Unique-per-user job name.
    job_type : str
        Catalog job-type slug.
    payload : dict
        Job-specific parameters.
    resource : str
        Compute resource (e.g. ``default``, ``cpu``, ``a10``).
    """

    job_name: str
    job_type: str
    payload: dict[str, Any]
    resource: str = "default"


class JobSubmitResponse(BaseModel):
    """Response from a single job/inference/utility submit.

    Attributes
    ----------
    process_id : str
        Server-assigned process identifier.
    """

    process_id: str


class JobSubmitMultipleResponse(BaseModel):
    """Response from batch job or inference submit.

    Attributes
    ----------
    process_ids : list of str
        Process identifiers in request order.
    """

    process_ids: list[str] = Field(default_factory=list)


class ListJobsResponse(BaseModel):
    """Response from listing user jobs.

    Attributes
    ----------
    job_names : list of str
        Job names.
    job_pids : list of str
        Corresponding process IDs.
    """

    job_names: list[str] = Field(default_factory=list)
    job_pids: list[str] = Field(default_factory=list)


class ProcessStatus(BaseModel):
    """Status payload for a pollable process.

    Attributes
    ----------
    process_id : str
        Process identifier.
    status : str
        Current status string (e.g. ``queued``, ``running``, ``completed``).
    message : str or None
        Optional status message.
    """

    process_id: str
    status: str
    message: str | None = None


class JobInfoResponse(BaseModel):
    """Detailed metadata for a job.

    Attributes
    ----------
    process_id : str
        Process identifier.
    info : dict
        Server-provided job metadata.
    """

    process_id: str
    info: dict[str, Any]


class MessageResponse(BaseModel):
    """Simple message response used by several endpoints.

    Attributes
    ----------
    message : str
        Human-readable message.
    """

    message: str


class BinaryResult(BaseModel):
    """Binary download result (job artifacts / ZIP bundles).

    Attributes
    ----------
    content : bytes
        Raw response body.
    filename : str or None
        Filename from ``Content-Disposition``, if present.
    media_type : str or None
        ``Content-Type`` header value, if present.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    content: bytes
    filename: str | None = None
    media_type: str | None = None


class InferenceSubmitRequest(BaseModel):
    """Single inference submission envelope.

    Attributes
    ----------
    model_type : str
        Model family (currently ``mpnn``).
    model_name : str
        Public or user model name.
    payload : dict
        Inference input parameters.
    """

    model_type: str
    model_name: str
    payload: dict[str, Any]


class ListProcessIdsResponse(BaseModel):
    """Response listing process identifiers.

    Attributes
    ----------
    process_ids : list of str
        Process identifiers for the current user.
    """

    process_ids: list[str] = Field(default_factory=list)


class DataResult(BaseModel):
    """JSON result wrapper for inference and utilities.

    Attributes
    ----------
    data : any
        Domain-specific result payload.
    """

    data: Any


class UsageLimitsResponse(BaseModel):
    """Usage statistics and monthly limits.

    Attributes
    ----------
    usage_limits : dict
        Server-provided usage/limit fields.
    """

    usage_limits: dict[str, Any]


class AuthCheckResponse(BaseModel):
    """Response from ``GET /auth/check``.

    Attributes
    ----------
    message : str or None
        Authentication confirmation message when present.
    """

    model_config = ConfigDict(extra="allow")

    message: str | None = None
