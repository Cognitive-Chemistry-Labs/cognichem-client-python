"""Models for CogniChem Assistant chat (``/chat``; JWT only)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatSession(BaseModel):
    """One Assistant thread.

    Attributes
    ----------
    id : str
        Session identifier.
    title : str or None
        Thread title.
    created_at, updated_at : str
        ISO-8601 timestamps.
    allow_structure_search : bool
        Whether the Assistant may send SMILES to external databases for
        similarity / substructure search in this thread.
    """

    id: str
    title: str | None = None
    created_at: str
    updated_at: str
    allow_structure_search: bool = False


class ChatSessionList(BaseModel):
    """The caller's Assistant threads.

    Attributes
    ----------
    items : list of ChatSession
        Threads.
    """

    items: list[ChatSession] = Field(default_factory=list)


class ChatMessage(BaseModel):
    """One persisted chat message.

    Attributes
    ----------
    id : str
        Message identifier.
    session_id : str
        Owning thread.
    turn_id : str or None
        Turn (wallet hold) the message belongs to.
    role : str
        ``user``, ``assistant``, ``tool``, or ``system``.
    content : str or None
        Message text.
    model_id : str or None
        Catalog model id.
    prompt_tokens, completion_tokens, cached_tokens, embedding_tokens : int or None
        Metered token counts.
    billed_usd : float or None
        USD debited for the turn.
    reasoning_effort : str or None
        Level the assistant turn was billed at.
    citations, tool_calls : list of dict or None
        Citation chips and tool call records.
    artifact_ids, job_ids, workflow_run_ids : list of str or None
        Linked resources.
    created_at : str
        ISO-8601 timestamp.
    """

    id: str
    session_id: str
    turn_id: str | None = None
    role: str
    content: str | None = None
    model_id: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cached_tokens: int | None = None
    embedding_tokens: int | None = None
    billed_usd: float | None = None
    reasoning_effort: str | None = None
    citations: list[dict[str, Any]] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    artifact_ids: list[str] | None = None
    job_ids: list[str] | None = None
    workflow_run_ids: list[str] | None = None
    created_at: str


class ChatMessageList(BaseModel):
    """History for one thread.

    Attributes
    ----------
    items : list of ChatMessage
        Messages, oldest first.
    """

    items: list[ChatMessage] = Field(default_factory=list)


class ChatEstimate(BaseModel):
    """Server quote for one Assistant turn's wallet hold.

    Attributes
    ----------
    model_id : str
        Catalog model id.
    reasoning_effort : str
        Reasoning level priced.
    tier : int
        Caller subscription tier.
    prompt_tokens : int
        Estimated prompt tokens (message plus history window).
    max_completion_tokens : int
        Completion token ceiling.
    hold_usd : float
        USD the turn would hold.
    """

    model_id: str
    reasoning_effort: str
    tier: int
    prompt_tokens: int
    max_completion_tokens: int
    hold_usd: float


class ChatSpendCap(BaseModel):
    """Assistant spend and spend cap of one thread (USD).

    Attributes
    ----------
    spent_usd : float
        Debited turns in this thread.
    held_usd : float
        Holds of turns still in flight.
    cap_usd : float
        Current thread spend cap.
    step_usd : float
        How much one Continue raises the cap.
    raised : bool
        Continue only: whether this request raised the cap.
    """

    spent_usd: float
    held_usd: float
    cap_usd: float
    step_usd: float
    raised: bool = False


class ChatCitation(BaseModel):
    """Citation chip on a proposal.

    Attributes
    ----------
    title : str or None
        Link title.
    url : str
        Public URL.
    """

    title: str | None = None
    url: str


class ChatRunProposal(BaseModel):
    """Assistant run proposal (plan card) awaiting the user's decision.

    Attributes
    ----------
    id : str
        Proposal identifier.
    session_id : str
        Owning thread.
    turn_id, message_id : str or None
        Turn and message that proposed it.
    kind : str
        ``job`` or ``workflow``.
    status : str
        ``pending``, ``approving``, ``submitted``, ``rejected``, ``expired``,
        or ``failed``.
    summary, display_name : str or None
        Plan text.
    job_type, resource : str or None
        Catalog job type and resource for job proposals.
    estimate_usd : float
        Server estimate; pass it back as ``accepted_estimate_usd`` to approve.
    estimate_breakdown : dict or None
        Per-step estimate for workflows.
    tier : int or None
        Tier the estimate used.
    accepted_estimate_usd, max_run_cost_usd : float or None
        Values recorded at approval.
    citations : list of ChatCitation
        Supporting links.
    failure_code, last_failure_code : str or None
        Failure details.
    job_id, workflow_run_id : str or None
        Enqueued run once submitted.
    expires_at, created_at : str
        ISO-8601 timestamps.
    payload_preview, params_preview, spec_outline : dict or None
        Previews of what would run.
    workflow_spec : dict or None
        Frozen WorkflowSpec (``include_spec=True`` only).
    """

    id: str
    session_id: str
    turn_id: str | None = None
    message_id: str | None = None
    kind: str
    status: str
    summary: str | None = None
    display_name: str | None = None
    job_type: str | None = None
    resource: str | None = None
    estimate_usd: float
    estimate_breakdown: dict[str, Any] | None = None
    tier: int | None = None
    accepted_estimate_usd: float | None = None
    max_run_cost_usd: float | None = None
    citations: list[ChatCitation] = Field(default_factory=list)
    failure_code: str | None = None
    last_failure_code: str | None = None
    job_id: str | None = None
    workflow_run_id: str | None = None
    expires_at: str
    created_at: str
    payload_preview: dict[str, Any] | None = None
    params_preview: dict[str, Any] | None = None
    spec_outline: dict[str, Any] | None = None
    workflow_spec: dict[str, Any] | None = None


class ChatRunProposalList(BaseModel):
    """Proposals for one thread.

    Attributes
    ----------
    items : list of ChatRunProposal
        Plan cards.
    """

    items: list[ChatRunProposal] = Field(default_factory=list)


class ChatTurnResult(BaseModel):
    """Collected outcome of one streamed Assistant turn.

    Attributes
    ----------
    turn_id : str or None
        Turn identifier (from the ``hold`` event).
    content : str
        Concatenated ``token`` deltas.
    hold_usd : float or None
        Wallet hold opened for the turn.
    billed_usd : float or None
        USD debited (from the ``done`` event).
    reasoning_effort : str or None
        Level the turn ran at.
    status : str or None
        ``done`` status when the turn was stopped or settled early.
    tool_calls : list of dict
        ``tool_call`` events (``name``, ``id``).
    citations : list of dict
        Citation events and ``done`` citations.
    proposals : list of dict
        ``proposal`` events (plan cards to approve or reject).
    done : dict or None
        Raw ``done`` payload (spend fields included).
    error : str or None
        Detail from an ``error`` event, if any.
    """

    turn_id: str | None = None
    content: str = ""
    hold_usd: float | None = None
    billed_usd: float | None = None
    reasoning_effort: str | None = None
    status: str | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    proposals: list[dict[str, Any]] = Field(default_factory=list)
    done: dict[str, Any] | None = None
    error: str | None = None
