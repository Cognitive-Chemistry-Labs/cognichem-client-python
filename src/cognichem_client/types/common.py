"""Core request/response models: auth, API keys, jobs, inference, utilities."""

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
        Enforced scopes (``read`` and/or ``write``).
    created_at : datetime
        Creation timestamp.
    last_used_at : datetime or None
        Last successful authentication time, if any.
    rotated_at : datetime or None
        Last rotation time, if any.
    expires_at : datetime or None
        When the key stops authenticating, if set.
    revoked_at : datetime or None
        Soft-revoke timestamp, if any.
    spend_ceiling_usd : float or None
        Per-key USD spend cap (``None`` means wallet-only).
    spend_accrued_usd : float or None
        USD accrued in the current spend window.
    allow_structure_search : bool
        Whether the key may send SMILES to ChEMBL similarity / substructure
        search via ``/lookup/chembl``.
    """

    id: str
    name: str
    key_prefix: str | None = None
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime
    last_used_at: datetime | None = None
    rotated_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    spend_ceiling_usd: float | None = None
    spend_accrued_usd: float | None = None
    allow_structure_search: bool = False


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


class JobEstimateResponse(BaseModel):
    """Wallet-reservation estimate for one job at the caller's tier.

    Attributes
    ----------
    cost : float
        Soft-hold estimate in USD.
    tier : int
        Caller subscription tier used for the rate.
    resource : str
        Resolved compute resource.
    job_type : str
        Catalog job type.
    expected_runtime_sec : float
        Catalog runtime assumption in seconds.
    rate_per_sec : float
        USD per second at ``tier`` and ``resource``.
    assumptions : dict
        Estimate basis (``validated`` is false for incomplete payloads).
    """

    cost: float
    tier: int
    resource: str
    job_type: str
    expected_runtime_sec: float
    rate_per_sec: float
    assumptions: dict[str, Any] = Field(default_factory=dict)


class JobListItem(BaseModel):
    """One Job Queue row.

    Attributes
    ----------
    process_id : str
        Job process identifier.
    job_name : str
        User-chosen job name.
    job_type : str
        Catalog job type.
    resource : str
        Compute resource.
    status : str
        ``queued``, ``dispatched``, ``running``, ``completed``, ``error``, or
        ``cancelled``.
    message : str
        Latest status message.
    created_at, started_at, finished_at : str or None
        ISO-8601 lifecycle timestamps.
    runtime_seconds : float
        Billed runtime so far.
    expected_billing_cost : float or None
        Reservation estimate (USD).
    charged_amount : float or None
        Final charge (USD) once billed.
    result_artifact_id : str or None
        Durable result artifact id, when stored.
    """

    process_id: str
    job_name: str
    job_type: str
    resource: str
    status: str
    message: str = ""
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    runtime_seconds: float = 0.0
    expected_billing_cost: float | None = None
    charged_amount: float | None = None
    result_artifact_id: str | None = None


class ListJobsResponse(BaseModel):
    """Paginated standalone jobs (workflow step jobs are excluded).

    Attributes
    ----------
    job_names : list of str
        Job names (parallel to ``job_pids``).
    job_pids : list of str
        Corresponding process IDs.
    items : list of JobListItem
        Full rows for the same page.
    total : int
        Total matching jobs.
    limit : int
        Page size.
    offset : int
        Page offset.
    """

    job_names: list[str] = Field(default_factory=list)
    job_pids: list[str] = Field(default_factory=list)
    items: list[JobListItem] = Field(default_factory=list)
    total: int = 0
    limit: int = 100
    offset: int = 0


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
    result_artifact_id : str or None
        Durable result artifact id for jobs, when stored. Inspect it with
        ``client.artifacts`` instead of downloading the whole zip.
    """

    process_id: str
    status: str
    message: str | None = None
    result_artifact_id: str | None = None


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


class HealthResponse(BaseModel):
    """Response from ``GET /health`` or ``GET /ready``.

    Attributes
    ----------
    status : str
        ``ok`` (health) or ``ready`` (readiness).
    """

    model_config = ConfigDict(extra="allow")

    status: str


class WalletBalance(BaseModel):
    """Wallet balance and USD reserved by in-flight jobs, runs and turns.

    Attributes
    ----------
    balance : float
        Wallet balance in USD.
    active_reserved : float
        USD currently held by active reservations.
    """

    balance: float
    active_reserved: float


class ServerSentEvent(BaseModel):
    """One ``text/event-stream`` frame.

    Attributes
    ----------
    event : str
        Event name (``message`` when the frame had no ``event:`` line).
    data : any
        Parsed JSON ``data``, or the raw string when it is not JSON.
    """

    event: str
    data: Any = None
