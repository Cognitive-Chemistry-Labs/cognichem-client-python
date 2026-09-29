"""Models for workflow validate / estimate / catalog, runs, and definitions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Diagnostic(BaseModel):
    """WorkflowSpec diagnostic (validation error or warning).

    Attributes
    ----------
    code : str
        Stable diagnostic code (e.g. ``cycle_detected``, ``missing_param``).
    message : str
        Human-readable explanation.
    step_id, port, path : str or None
        Where the problem is, when known.
    """

    code: str
    message: str
    step_id: str | None = None
    port: str | None = None
    path: str | None = None


class WorkflowValidation(BaseModel):
    """Result of ``POST /workflows/validate``.

    Attributes
    ----------
    valid : bool
        Whether the spec is valid.
    errors : list of Diagnostic
        Blocking problems (empty when ``valid``).
    warnings : list of Diagnostic
        Non-blocking notes.
    order : list of str
        Topological step order (empty when invalid).
    step_count : int
        Number of steps in the spec.
    """

    valid: bool
    errors: list[Diagnostic] = Field(default_factory=list)
    warnings: list[Diagnostic] = Field(default_factory=list)
    order: list[str] = Field(default_factory=list)
    step_count: int = 0


class WorkflowStepCost(BaseModel):
    """Per-step cost line of a workflow estimate.

    Attributes
    ----------
    step_id : str
        Step identifier.
    cost : float
        Soft-hold USD for the step.
    """

    step_id: str
    cost: float


class WorkflowEstimate(BaseModel):
    """Upper-bound soft-hold estimate for a WorkflowSpec.

    Attributes
    ----------
    total : float
        Total USD hold.
    per_step : list of WorkflowStepCost
        Cost per step.
    tier : int
        Caller subscription tier.
    assumptions : list of dict
        Per-step estimate basis (``reason``, ``multiplier``, ``unit_cost``,
        fan-out caps, unresolved binds, …).
    timing_assumptions : list of dict
        Coarse concurrency advisories (not dollars, not an ETA).
    warnings : list of Diagnostic
        Estimate warnings (e.g. ``storage_quota_soft``).
    """

    total: float
    per_step: list[WorkflowStepCost] = Field(default_factory=list)
    tier: int
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    timing_assumptions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[Diagnostic] = Field(default_factory=list)


class WorkflowTemplateStep(BaseModel):
    """One step outline of a curated template.

    Attributes
    ----------
    id : str
        Step identifier.
    type : str
        Step type (``job``, ``filter``, …).
    job_type : str or None
        Catalog job type for job steps.
    op : str or None
        Operation for non-job steps.
    """

    id: str
    type: str
    job_type: str | None = None
    op: str | None = None


class WorkflowTemplateSummary(BaseModel):
    """Curated template outline (no spec body).

    Attributes
    ----------
    id : str
        Template identifier.
    name : str
        Display name.
    summary : str
        One-line description.
    complexity : str
        ``simple``, ``moderate``, or ``advanced``.
    steps : list of WorkflowTemplateStep
        Step outline.
    params : list of str
        Runtime params the template declares.
    """

    id: str
    name: str
    summary: str
    complexity: str
    steps: list[WorkflowTemplateStep] = Field(default_factory=list)
    params: list[str] = Field(default_factory=list)


class WorkflowTemplate(BaseModel):
    """Curated template with its full WorkflowSpec.

    Attributes
    ----------
    id : str
        Template identifier.
    name : str
        Display name.
    summary : str
        One-line description.
    complexity : str
        Template complexity.
    spec : dict
        WorkflowSpec to validate, estimate, or run.
    """

    id: str
    name: str
    summary: str
    complexity: str
    spec: dict[str, Any]


class WorkflowNodePorts(BaseModel):
    """Catalog workflow input / output ports for one job type.

    Attributes
    ----------
    job_type : str
        Catalog job type.
    inputs : dict
        Input ports (kind, formats, payload field, cardinality, …).
    outputs : dict
        Output ports (kind, format, metrics, resolver).
    """

    job_type: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunStep(BaseModel):
    """One step row of a workflow run.

    Attributes
    ----------
    id : str
        Step row identifier.
    step_key : str
        Spec step id.
    step_index : int
        Fan-out index.
    status : str
        Step status.
    job_type : str or None
        Catalog job type.
    job_id : str or None
        Linked job process id.
    status_message : str
        Latest status message.
    """

    id: str
    step_key: str
    step_index: int = 0
    status: str
    job_type: str | None = None
    job_id: str | None = None
    status_message: str = ""


class WorkflowRun(BaseModel):
    """Workflow run with step summary (create / get / resume).

    Attributes
    ----------
    id : str
        Run identifier.
    run_name : str
        User-chosen run name.
    status : str
        ``pending``, ``running``, ``paused``, ``completed``, ``failed``, or
        ``cancelled``.
    status_message : str
        Latest status message.
    step_counts : dict
        Step counts by status.
    remaining_hold, estimated_cost, charged_amount : float
        Wallet amounts in USD.
    max_run_cost : float or None
        Spend cap; the run pauses when it would be exceeded.
    steps : list of WorkflowRunStep
        Step rows.
    created_at, updated_at, finished_at : str or None
        ISO-8601 timestamps.
    spec : dict or None
        Frozen spec (only with ``include_spec=True``).
    definition_id : str or None
        Saved definition, when the run came from one (``include_spec=True``).
    warnings : list of dict
        Create-time warnings (e.g. ``storage_quota_soft``).
    """

    id: str
    run_name: str
    status: str
    status_message: str = ""
    step_counts: dict[str, Any] = Field(default_factory=dict)
    remaining_hold: float = 0.0
    estimated_cost: float = 0.0
    charged_amount: float = 0.0
    max_run_cost: float | None = None
    steps: list[WorkflowRunStep] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None
    spec: dict[str, Any] | None = None
    definition_id: str | None = None
    warnings: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowRunListItem(BaseModel):
    """Workflow run list row (no spec, params, or steps).

    Attributes
    ----------
    id : str
        Run identifier.
    run_name : str
        Run name.
    status : str
        Run status.
    status_message : str
        Latest status message.
    step_counts : dict
        Step counts by status.
    estimated_cost, charged_amount, remaining_hold : float
        Wallet amounts in USD.
    max_run_cost : float or None
        Spend cap.
    created_at, updated_at, finished_at : str or None
        ISO-8601 timestamps.
    definition_id : str or None
        Saved definition, if any.
    """

    id: str
    run_name: str
    status: str
    status_message: str = ""
    step_counts: dict[str, Any] = Field(default_factory=dict)
    estimated_cost: float = 0.0
    charged_amount: float = 0.0
    remaining_hold: float = 0.0
    max_run_cost: float | None = None
    created_at: str | None = None
    updated_at: str | None = None
    finished_at: str | None = None
    definition_id: str | None = None


class WorkflowRunList(BaseModel):
    """Paginated workflow runs.

    Attributes
    ----------
    items : list of WorkflowRunListItem
        Page rows.
    total : int
        Total matching runs.
    limit : int
        Page size.
    offset : int
        Page offset.
    """

    items: list[WorkflowRunListItem] = Field(default_factory=list)
    total: int = 0
    limit: int = 0
    offset: int = 0


class WorkflowRunArtifact(BaseModel):
    """One artifact port produced by a workflow run.

    Attributes
    ----------
    artifact_id : str
        Artifact identifier.
    step_key : str or None
        Producing spec step id.
    step_index : int or None
        Fan-out index.
    port : str
        Manifest port.
    data_kind, data_format : str
        Port kind and format.
    record_count, size_bytes : int
        Records and stored size.
    is_virtual : bool
        Whether the artifact is a view over a parent.
    expires_at : str or None
        ISO-8601 expiry.
    job_id : str or None
        Producing job.
    """

    artifact_id: str
    step_key: str | None = None
    step_index: int | None = None
    port: str
    data_kind: str
    data_format: str
    record_count: int = 0
    size_bytes: int = 0
    is_virtual: bool = False
    expires_at: str | None = None
    job_id: str | None = None


class WorkflowRunArtifacts(BaseModel):
    """Run-scoped artifact list.

    Attributes
    ----------
    items : list of WorkflowRunArtifact
        Artifact ports.
    """

    items: list[WorkflowRunArtifact] = Field(default_factory=list)


class WorkflowRunCancelResponse(BaseModel):
    """Response from ``POST /workflows/runs/{run_id}/cancel``.

    Attributes
    ----------
    run_id : str
        Run identifier.
    status : str
        Run status after the request.
    cancelled_job_ids : list of str
        Step jobs that were cancelled.
    message : str
        Server message.
    """

    run_id: str
    status: str
    cancelled_job_ids: list[str] = Field(default_factory=list)
    message: str = ""


class WorkflowDefinition(BaseModel):
    """Saved workflow definition (``wfd-…``).

    Attributes
    ----------
    id : str
        Definition identifier.
    user_id : str
        Owner.
    name : str
        Unique per-user name.
    description : str
        Description.
    spec : dict
        WorkflowSpec.
    spec_version : int
        Spec schema version.
    graph_layout : dict or None
        Builder layout.
    visibility : str
        ``private`` or ``link``.
    share_token : str or None
        Share token (owner responses when ``visibility`` is ``link``).
    created_at, updated_at : str or None
        ISO-8601 timestamps.
    """

    id: str
    user_id: str
    name: str
    description: str = ""
    spec: dict[str, Any] = Field(default_factory=dict)
    spec_version: int = 1
    graph_layout: dict[str, Any] | None = None
    visibility: str = "private"
    share_token: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class WorkflowDefinitionListItem(BaseModel):
    """Definition list row (no spec or share token).

    Attributes
    ----------
    id : str
        Definition identifier.
    user_id : str
        Owner.
    name : str
        Name.
    description : str
        Description.
    spec_version : int
        Spec schema version.
    graph_layout : dict or None
        Builder layout.
    visibility : str
        ``private`` or ``link``.
    created_at, updated_at : str or None
        ISO-8601 timestamps.
    """

    id: str
    user_id: str
    name: str
    description: str = ""
    spec_version: int = 1
    graph_layout: dict[str, Any] | None = None
    visibility: str = "private"
    created_at: str | None = None
    updated_at: str | None = None


class WorkflowDefinitionList(BaseModel):
    """Paginated workflow definitions.

    Attributes
    ----------
    items : list of WorkflowDefinitionListItem
        Page rows.
    total : int
        Total definitions.
    limit : int
        Page size.
    offset : int
        Page offset.
    """

    items: list[WorkflowDefinitionListItem] = Field(default_factory=list)
    total: int = 0
    limit: int = 0
    offset: int = 0


class WorkflowDefinitionVersionListItem(BaseModel):
    """Definition version metadata.

    Attributes
    ----------
    version : int
        Version number.
    created_at : str or None
        ISO-8601 timestamp.
    created_by_user_id : str or None
        Author.
    """

    version: int
    created_at: str | None = None
    created_by_user_id: str | None = None


class WorkflowDefinitionVersionList(BaseModel):
    """Paginated definition versions.

    Attributes
    ----------
    items : list of WorkflowDefinitionVersionListItem
        Page rows.
    total : int
        Total versions.
    limit : int
        Page size.
    offset : int
        Page offset.
    """

    items: list[WorkflowDefinitionVersionListItem] = Field(default_factory=list)
    total: int = 0
    limit: int = 0
    offset: int = 0


class WorkflowDefinitionVersion(BaseModel):
    """Full definition version snapshot.

    Attributes
    ----------
    definition_id : str
        Definition identifier.
    version : int
        Version number.
    spec : dict
        WorkflowSpec at this version.
    graph_layout : dict or None
        Builder layout at this version.
    created_at : str or None
        ISO-8601 timestamp.
    created_by_user_id : str or None
        Author.
    """

    definition_id: str
    version: int
    spec: dict[str, Any] = Field(default_factory=dict)
    graph_layout: dict[str, Any] | None = None
    created_at: str | None = None
    created_by_user_id: str | None = None
