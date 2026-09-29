"""CogniChem Assistant chat resource clients under ``/chat`` (JWT only)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient, ensure_idempotency_key
from cognichem_client.constants import (
    DEFAULT_ASSISTANT_MODEL_ID,
    ROUTES,
    ReasoningEffort,
)
from cognichem_client.errors import CogniChemError
from cognichem_client.types import (
    ChatEstimate,
    ChatMessageList,
    ChatRunProposal,
    ChatRunProposalList,
    ChatSession,
    ChatSessionList,
    ChatSpendCap,
    ChatTurnResult,
    ServerSentEvent,
)

# Turns end within the server's 180 s deadline, but tool rounds can leave
# the stream quiet for a while; allow longer than the default read timeout.
_TURN_READ_TIMEOUT = 240.0


def _turn_body(
    message: str,
    reasoning_effort: ReasoningEffort | None,
    artifact_ids: Sequence[str],
    model_id: str,
) -> dict[str, Any]:
    """Build a turn / estimate body.

    Parameters
    ----------
    message : str
        User message.
    reasoning_effort : str or None
        Reasoning level.
    artifact_ids : sequence of str
        Attached artifacts.
    model_id : str
        Catalog model id.

    Returns
    -------
    dict
        JSON body.
    """
    body: dict[str, Any] = {
        "message": message,
        "model_id": model_id,
        "artifact_ids": list(artifact_ids),
    }
    if reasoning_effort is not None:
        body["reasoning_effort"] = reasoning_effort
    return body


class _TurnCollector:
    """Fold turn events into a :class:`ChatTurnResult`."""

    def __init__(self) -> None:
        """Start an empty result."""
        self._result = ChatTurnResult()
        self._parts: list[str] = []

    def add(self, event: ServerSentEvent) -> None:
        """Apply one event.

        Parameters
        ----------
        event : ServerSentEvent
            Turn event.
        """
        data = event.data if isinstance(event.data, dict) else {}
        result = self._result
        if event.event == "hold":
            result.turn_id = data.get("turn_id")
            result.hold_usd = data.get("hold_usd")
            result.reasoning_effort = data.get("reasoning_effort")
        elif event.event == "token":
            self._parts.append(str(data.get("delta") or ""))
        elif event.event == "tool_call":
            result.tool_calls.append(data)
        elif event.event == "citation":
            result.citations.append(data)
        elif event.event == "proposal":
            result.proposals.append(data)
        elif event.event == "done":
            result.done = data
            result.turn_id = data.get("turn_id") or result.turn_id
            result.billed_usd = data.get("billed_usd")
            result.status = data.get("status")
            if isinstance(data.get("citations"), list):
                result.citations = list(data["citations"])
        elif event.event == "error":
            result.error = str(data.get("detail") or event.data)

    def finish(self) -> ChatTurnResult:
        """Return the collected result.

        Returns
        -------
        ChatTurnResult
            Collected turn.

        Raises
        ------
        CogniChemError
            If the stream carried an ``error`` event.
        """
        self._result.content = "".join(self._parts)
        if self._result.error is not None:
            raise CogniChemError(
                self._result.error,
                detail=self._result.error,
                code="assistant-turn-error",
                body=self._result.model_dump(),
            )
        return self._result


class ChatSessionsResource:
    """Synchronous Assistant thread endpoints under ``/chat/sessions``.

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

    def list(self) -> ChatSessionList:
        """List the caller's Assistant threads.

        Returns
        -------
        ChatSessionList
            Threads.
        """
        data = self._http.request("GET", ROUTES["chat_sessions"], prefer_bearer=True)
        return ChatSessionList.model_validate(data)

    def create(self, title: str | None = None) -> ChatSession:
        """Create an Assistant thread.

        Parameters
        ----------
        title : str or None, optional
            Thread title (up to 200 characters).

        Returns
        -------
        ChatSession
            The new thread.
        """
        data = self._http.request(
            "POST",
            ROUTES["chat_sessions"],
            json={"title": title},
            prefer_bearer=True,
        )
        return ChatSession.model_validate(data)

    def get(self, session_id: str) -> ChatSession:
        """Fetch one Assistant thread.

        Parameters
        ----------
        session_id : str
            Session identifier.

        Returns
        -------
        ChatSession
            The thread.
        """
        data = self._http.request(
            "GET",
            ROUTES["chat_session"].format(session_id=session_id),
            prefer_bearer=True,
        )
        return ChatSession.model_validate(data)

    def update(
        self,
        session_id: str,
        *,
        title: str | None = None,
        allow_structure_search: bool | None = None,
    ) -> ChatSession:
        """Rename a thread and/or change its structure-search opt-in.

        Parameters
        ----------
        session_id : str
            Session identifier.
        title : str or None, optional
            New title.
        allow_structure_search : bool or None, optional
            Let the Assistant send SMILES to external databases for
            similarity / substructure search in this thread.

        Returns
        -------
        ChatSession
            The updated thread.

        Raises
        ------
        ValueError
            If neither field is given.
        """
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if allow_structure_search is not None:
            body["allow_structure_search"] = allow_structure_search
        if not body:
            raise ValueError("Provide title and/or allow_structure_search")
        data = self._http.request(
            "PATCH",
            ROUTES["chat_session"].format(session_id=session_id),
            json=body,
            prefer_bearer=True,
        )
        return ChatSession.model_validate(data)

    def delete(self, session_id: str) -> None:
        """Delete a thread with its messages.

        Parameters
        ----------
        session_id : str
            Session identifier.

        Returns
        -------
        None
            The API answers 204 No Content.
        """
        self._http.request(
            "DELETE",
            ROUTES["chat_session"].format(session_id=session_id),
            prefer_bearer=True,
        )

    def messages(self, session_id: str) -> ChatMessageList:
        """Return a thread's message history.

        Parameters
        ----------
        session_id : str
            Session identifier.

        Returns
        -------
        ChatMessageList
            Messages, oldest first.
        """
        data = self._http.request(
            "GET",
            ROUTES["chat_messages"].format(session_id=session_id),
            prefer_bearer=True,
        )
        return ChatMessageList.model_validate(data)


class ChatProposalsResource:
    """Synchronous Assistant run proposal (plan card) endpoints.

    The Assistant only proposes jobs and workflow runs; nothing runs until
    you approve the proposal at its server estimate.

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

    def list(self, session_id: str) -> ChatRunProposalList:
        """List the proposals in a thread.

        Parameters
        ----------
        session_id : str
            Session identifier.

        Returns
        -------
        ChatRunProposalList
            Plan cards.
        """
        data = self._http.request(
            "GET",
            ROUTES["chat_proposals"].format(session_id=session_id),
            prefer_bearer=True,
        )
        return ChatRunProposalList.model_validate(data)

    def get(
        self, session_id: str, proposal_id: str, *, include_spec: bool = False
    ) -> ChatRunProposal:
        """Fetch one proposal.

        Parameters
        ----------
        session_id : str
            Session identifier.
        proposal_id : str
            Proposal identifier.
        include_spec : bool, optional
            Include the frozen WorkflowSpec (``workflow_spec``).

        Returns
        -------
        ChatRunProposal
            The plan card.
        """
        data = self._http.request(
            "GET",
            ROUTES["chat_proposal"].format(
                session_id=session_id, proposal_id=proposal_id
            ),
            params={"include_spec": "true"} if include_spec else None,
            prefer_bearer=True,
        )
        return ChatRunProposal.model_validate(data)

    def approve(
        self,
        session_id: str,
        proposal_id: str,
        accepted_estimate_usd: float,
        *,
        max_run_cost_usd: float | None = None,
        idempotency_key: str | None = None,
    ) -> ChatRunProposal:
        """Approve a proposal: re-validate, re-estimate, then enqueue the run.

        Parameters
        ----------
        session_id : str
            Session identifier.
        proposal_id : str
            Proposal identifier.
        accepted_estimate_usd : float
            The ``estimate_usd`` you reviewed. If the server estimate has
            risen, nothing runs and a
            :class:`~cognichem_client.errors.ConflictError` with code
            ``estimate-changed`` carries the new ``proposal`` in ``body``.
        max_run_cost_usd : float or None, optional
            Workflow spend cap (defaults to the estimate total).
        idempotency_key : str or None, optional
            Idempotency key (required by the API; generated when omitted).

        Returns
        -------
        ChatRunProposal
            The proposal with ``job_id`` or ``workflow_run_id`` once submitted.
        """
        data = self._http.request(
            "POST",
            ROUTES["chat_proposal_approve"].format(
                session_id=session_id, proposal_id=proposal_id
            ),
            json={
                "accepted_estimate_usd": accepted_estimate_usd,
                "max_run_cost_usd": max_run_cost_usd,
            },
            idempotency_key=ensure_idempotency_key(idempotency_key),
            prefer_bearer=True,
        )
        return ChatRunProposal.model_validate(data)

    def reject(self, session_id: str, proposal_id: str) -> ChatRunProposal:
        """Dismiss a pending proposal (no spend).

        Parameters
        ----------
        session_id : str
            Session identifier.
        proposal_id : str
            Proposal identifier.

        Returns
        -------
        ChatRunProposal
            The rejected proposal.
        """
        data = self._http.request(
            "POST",
            ROUTES["chat_proposal_reject"].format(
                session_id=session_id, proposal_id=proposal_id
            ),
            prefer_bearer=True,
        )
        return ChatRunProposal.model_validate(data)


class ChatResource:
    """Synchronous CogniChem Assistant chat endpoints under ``/chat``.

    Chat is JWT-only: sign in with ``client.auth.login_email`` (or pass
    ``access_token``) first. Each turn holds wallet funds at your tier's
    token rate, debits the metered tokens, and releases the rest.

    Parameters
    ----------
    http : HttpClient
        Shared HTTP transport.

    Attributes
    ----------
    sessions : ChatSessionsResource
        Thread endpoints.
    proposals : ChatProposalsResource
        Run proposal endpoints.
    """

    def __init__(self, http: HttpClient) -> None:
        """Attach the shared HTTP transport and nested resources.

        Parameters
        ----------
        http : HttpClient
            Shared HTTP transport.
        """
        self._http = http
        self.sessions = ChatSessionsResource(http)
        self.proposals = ChatProposalsResource(http)

    def estimate(
        self,
        session_id: str,
        message: str,
        *,
        reasoning_effort: ReasoningEffort | None = None,
        artifact_ids: Sequence[str] = (),
        model_id: str = DEFAULT_ASSISTANT_MODEL_ID,
    ) -> ChatEstimate:
        """Quote the wallet hold for a turn without starting it.

        Parameters
        ----------
        session_id : str
            Session identifier.
        message : str
            User message (up to 16,000 characters).
        reasoning_effort : {"low", "medium", "high"} or None, optional
            Reasoning level (catalog default ``low``).
        artifact_ids : sequence of str, optional
            Artifacts to attach.
        model_id : str, optional
            Catalog model id.

        Returns
        -------
        ChatEstimate
            Hold in USD and the token assumptions.
        """
        data = self._http.request(
            "POST",
            ROUTES["chat_estimate"].format(session_id=session_id),
            json=_turn_body(message, reasoning_effort, artifact_ids, model_id),
            prefer_bearer=True,
        )
        return ChatEstimate.model_validate(data)

    def stream(
        self,
        session_id: str,
        message: str,
        *,
        reasoning_effort: ReasoningEffort | None = None,
        artifact_ids: Sequence[str] = (),
        model_id: str = DEFAULT_ASSISTANT_MODEL_ID,
    ) -> Iterator[ServerSentEvent]:
        """Start a turn and yield its server-sent events as they arrive.

        Events: ``hold`` (``turn_id``, ``hold_usd``), ``token`` (``delta``),
        ``tool_call``, ``citation``, ``proposal``, ``done`` (``billed_usd``,
        spend fields), and ``error`` (``detail``).

        Parameters
        ----------
        session_id : str
            Session identifier.
        message : str
            User message (up to 16,000 characters).
        reasoning_effort : {"low", "medium", "high"} or None, optional
            Reasoning level (catalog default ``low``).
        artifact_ids : sequence of str, optional
            Artifacts to attach (bound as ``$artifact`` in proposals).
        model_id : str, optional
            Catalog model id.

        Yields
        ------
        ServerSentEvent
            Turn events in order.

        Raises
        ------
        PaymentRequiredError
            If the wallet cannot cover the hold.
        ConflictError
            If the thread is at its spend cap (code ``session-spend-cap``;
            call :meth:`continue_spend_cap` to raise it).
        """
        return self._http.stream_events(
            "POST",
            ROUTES["chat_turns"].format(session_id=session_id),
            json=_turn_body(message, reasoning_effort, artifact_ids, model_id),
            prefer_bearer=True,
            timeout=_TURN_READ_TIMEOUT,
        )

    def send(
        self,
        session_id: str,
        message: str,
        *,
        reasoning_effort: ReasoningEffort | None = None,
        artifact_ids: Sequence[str] = (),
        model_id: str = DEFAULT_ASSISTANT_MODEL_ID,
    ) -> ChatTurnResult:
        """Run one turn to completion and return the collected reply.

        Parameters
        ----------
        session_id : str
            Session identifier.
        message : str
            User message (up to 16,000 characters).
        reasoning_effort : {"low", "medium", "high"} or None, optional
            Reasoning level (catalog default ``low``).
        artifact_ids : sequence of str, optional
            Artifacts to attach.
        model_id : str, optional
            Catalog model id.

        Returns
        -------
        ChatTurnResult
            Reply text, spend, tool calls, citations, and proposals.

        Raises
        ------
        CogniChemError
            If the stream ends with an ``error`` event (code
            ``assistant-turn-error``), or on HTTP errors as in :meth:`stream`.
        """
        collector = _TurnCollector()
        for event in self.stream(
            session_id,
            message,
            reasoning_effort=reasoning_effort,
            artifact_ids=artifact_ids,
            model_id=model_id,
        ):
            collector.add(event)
        return collector.finish()

    def stop(self, session_id: str, turn_id: str) -> dict[str, str]:
        """Interrupt an in-flight turn; metered tokens bill, the rest releases.

        Parameters
        ----------
        session_id : str
            Session identifier.
        turn_id : str
            Turn identifier (from the ``hold`` event).

        Returns
        -------
        dict
            ``{"status": "stopping", "turn_id": ...}``.
        """
        data = self._http.request(
            "POST",
            ROUTES["chat_turn_stop"].format(session_id=session_id, turn_id=turn_id),
            prefer_bearer=True,
        )
        assert isinstance(data, dict)
        return data

    def spend_cap(
        self, session_id: str, *, model_id: str = DEFAULT_ASSISTANT_MODEL_ID
    ) -> ChatSpendCap:
        """Return a thread's Assistant spend and spend cap.

        Parameters
        ----------
        session_id : str
            Session identifier.
        model_id : str, optional
            Catalog model id.

        Returns
        -------
        ChatSpendCap
            Spent, held, cap, and step (USD).
        """
        data = self._http.request(
            "GET",
            ROUTES["chat_spend_cap"].format(session_id=session_id),
            params={"model_id": model_id},
            prefer_bearer=True,
        )
        return ChatSpendCap.model_validate(data)

    def continue_spend_cap(
        self,
        session_id: str,
        current_cap_usd: float,
        *,
        model_id: str = DEFAULT_ASSISTANT_MODEL_ID,
    ) -> ChatSpendCap:
        """Raise a thread's spend cap by one step (the user's Continue).

        Parameters
        ----------
        session_id : str
            Session identifier.
        current_cap_usd : float
            The cap you saw. If it has already moved, nothing changes and
            ``raised`` is false.
        model_id : str, optional
            Catalog model id.

        Returns
        -------
        ChatSpendCap
            State after the request.
        """
        data = self._http.request(
            "POST",
            ROUTES["chat_spend_cap_continue"].format(session_id=session_id),
            json={"current_cap_usd": current_cap_usd, "model_id": model_id},
            prefer_bearer=True,
        )
        return ChatSpendCap.model_validate(data)


class AsyncChatSessionsResource:
    """Asynchronous Assistant thread endpoints under ``/chat/sessions``.

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

    async def list(self) -> ChatSessionList:
        """List the caller's Assistant threads.

        Returns
        -------
        ChatSessionList
            Threads.
        """
        data = await self._http.request(
            "GET", ROUTES["chat_sessions"], prefer_bearer=True
        )
        return ChatSessionList.model_validate(data)

    async def create(self, title: str | None = None) -> ChatSession:
        """Create an Assistant thread.

        Parameters
        ----------
        title : str or None, optional
            Thread title (up to 200 characters).

        Returns
        -------
        ChatSession
            The new thread.
        """
        data = await self._http.request(
            "POST",
            ROUTES["chat_sessions"],
            json={"title": title},
            prefer_bearer=True,
        )
        return ChatSession.model_validate(data)

    async def get(self, session_id: str) -> ChatSession:
        """Fetch one Assistant thread.

        Parameters
        ----------
        session_id : str
            Session identifier.

        Returns
        -------
        ChatSession
            The thread.
        """
        data = await self._http.request(
            "GET",
            ROUTES["chat_session"].format(session_id=session_id),
            prefer_bearer=True,
        )
        return ChatSession.model_validate(data)

    async def update(
        self,
        session_id: str,
        *,
        title: str | None = None,
        allow_structure_search: bool | None = None,
    ) -> ChatSession:
        """Rename a thread and/or change its structure-search opt-in.

        Parameters
        ----------
        session_id : str
            Session identifier.
        title : str or None, optional
            New title.
        allow_structure_search : bool or None, optional
            Let the Assistant send SMILES to external databases for
            similarity / substructure search in this thread.

        Returns
        -------
        ChatSession
            The updated thread.

        Raises
        ------
        ValueError
            If neither field is given.
        """
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = title
        if allow_structure_search is not None:
            body["allow_structure_search"] = allow_structure_search
        if not body:
            raise ValueError("Provide title and/or allow_structure_search")
        data = await self._http.request(
            "PATCH",
            ROUTES["chat_session"].format(session_id=session_id),
            json=body,
            prefer_bearer=True,
        )
        return ChatSession.model_validate(data)

    async def delete(self, session_id: str) -> None:
        """Delete a thread with its messages.

        Parameters
        ----------
        session_id : str
            Session identifier.

        Returns
        -------
        None
            The API answers 204 No Content.
        """
        await self._http.request(
            "DELETE",
            ROUTES["chat_session"].format(session_id=session_id),
            prefer_bearer=True,
        )

    async def messages(self, session_id: str) -> ChatMessageList:
        """Return a thread's message history.

        Parameters
        ----------
        session_id : str
            Session identifier.

        Returns
        -------
        ChatMessageList
            Messages, oldest first.
        """
        data = await self._http.request(
            "GET",
            ROUTES["chat_messages"].format(session_id=session_id),
            prefer_bearer=True,
        )
        return ChatMessageList.model_validate(data)


class AsyncChatProposalsResource:
    """Asynchronous Assistant run proposal (plan card) endpoints.

    The Assistant only proposes jobs and workflow runs; nothing runs until
    you approve the proposal at its server estimate.

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

    async def list(self, session_id: str) -> ChatRunProposalList:
        """List the proposals in a thread.

        Parameters
        ----------
        session_id : str
            Session identifier.

        Returns
        -------
        ChatRunProposalList
            Plan cards.
        """
        data = await self._http.request(
            "GET",
            ROUTES["chat_proposals"].format(session_id=session_id),
            prefer_bearer=True,
        )
        return ChatRunProposalList.model_validate(data)

    async def get(
        self, session_id: str, proposal_id: str, *, include_spec: bool = False
    ) -> ChatRunProposal:
        """Fetch one proposal.

        Parameters
        ----------
        session_id : str
            Session identifier.
        proposal_id : str
            Proposal identifier.
        include_spec : bool, optional
            Include the frozen WorkflowSpec (``workflow_spec``).

        Returns
        -------
        ChatRunProposal
            The plan card.
        """
        data = await self._http.request(
            "GET",
            ROUTES["chat_proposal"].format(
                session_id=session_id, proposal_id=proposal_id
            ),
            params={"include_spec": "true"} if include_spec else None,
            prefer_bearer=True,
        )
        return ChatRunProposal.model_validate(data)

    async def approve(
        self,
        session_id: str,
        proposal_id: str,
        accepted_estimate_usd: float,
        *,
        max_run_cost_usd: float | None = None,
        idempotency_key: str | None = None,
    ) -> ChatRunProposal:
        """Approve a proposal: re-validate, re-estimate, then enqueue the run.

        Parameters
        ----------
        session_id : str
            Session identifier.
        proposal_id : str
            Proposal identifier.
        accepted_estimate_usd : float
            The ``estimate_usd`` you reviewed. If the server estimate has
            risen, nothing runs and a
            :class:`~cognichem_client.errors.ConflictError` with code
            ``estimate-changed`` carries the new ``proposal`` in ``body``.
        max_run_cost_usd : float or None, optional
            Workflow spend cap (defaults to the estimate total).
        idempotency_key : str or None, optional
            Idempotency key (required by the API; generated when omitted).

        Returns
        -------
        ChatRunProposal
            The proposal with ``job_id`` or ``workflow_run_id`` once submitted.
        """
        data = await self._http.request(
            "POST",
            ROUTES["chat_proposal_approve"].format(
                session_id=session_id, proposal_id=proposal_id
            ),
            json={
                "accepted_estimate_usd": accepted_estimate_usd,
                "max_run_cost_usd": max_run_cost_usd,
            },
            idempotency_key=ensure_idempotency_key(idempotency_key),
            prefer_bearer=True,
        )
        return ChatRunProposal.model_validate(data)

    async def reject(self, session_id: str, proposal_id: str) -> ChatRunProposal:
        """Dismiss a pending proposal (no spend).

        Parameters
        ----------
        session_id : str
            Session identifier.
        proposal_id : str
            Proposal identifier.

        Returns
        -------
        ChatRunProposal
            The rejected proposal.
        """
        data = await self._http.request(
            "POST",
            ROUTES["chat_proposal_reject"].format(
                session_id=session_id, proposal_id=proposal_id
            ),
            prefer_bearer=True,
        )
        return ChatRunProposal.model_validate(data)


class AsyncChatResource:
    """Asynchronous CogniChem Assistant chat endpoints under ``/chat``.

    Chat is JWT-only: sign in with ``client.auth.login_email`` (or pass
    ``access_token``) first. Each turn holds wallet funds at your tier's
    token rate, debits the metered tokens, and releases the rest.

    Parameters
    ----------
    http : AsyncHttpClient
        Shared async HTTP transport.

    Attributes
    ----------
    sessions : AsyncChatSessionsResource
        Thread endpoints.
    proposals : AsyncChatProposalsResource
        Run proposal endpoints.
    """

    def __init__(self, http: AsyncHttpClient) -> None:
        """Attach the shared async HTTP transport and nested resources.

        Parameters
        ----------
        http : AsyncHttpClient
            Shared async HTTP transport.
        """
        self._http = http
        self.sessions = AsyncChatSessionsResource(http)
        self.proposals = AsyncChatProposalsResource(http)

    async def estimate(
        self,
        session_id: str,
        message: str,
        *,
        reasoning_effort: ReasoningEffort | None = None,
        artifact_ids: Sequence[str] = (),
        model_id: str = DEFAULT_ASSISTANT_MODEL_ID,
    ) -> ChatEstimate:
        """Quote the wallet hold for a turn without starting it.

        Parameters
        ----------
        session_id : str
            Session identifier.
        message : str
            User message (up to 16,000 characters).
        reasoning_effort : {"low", "medium", "high"} or None, optional
            Reasoning level (catalog default ``low``).
        artifact_ids : sequence of str, optional
            Artifacts to attach.
        model_id : str, optional
            Catalog model id.

        Returns
        -------
        ChatEstimate
            Hold in USD and the token assumptions.
        """
        data = await self._http.request(
            "POST",
            ROUTES["chat_estimate"].format(session_id=session_id),
            json=_turn_body(message, reasoning_effort, artifact_ids, model_id),
            prefer_bearer=True,
        )
        return ChatEstimate.model_validate(data)

    def stream(
        self,
        session_id: str,
        message: str,
        *,
        reasoning_effort: ReasoningEffort | None = None,
        artifact_ids: Sequence[str] = (),
        model_id: str = DEFAULT_ASSISTANT_MODEL_ID,
    ) -> AsyncIterator[ServerSentEvent]:
        """Start a turn and yield its server-sent events as they arrive.

        Events: ``hold`` (``turn_id``, ``hold_usd``), ``token`` (``delta``),
        ``tool_call``, ``citation``, ``proposal``, ``done`` (``billed_usd``,
        spend fields), and ``error`` (``detail``).

        Parameters
        ----------
        session_id : str
            Session identifier.
        message : str
            User message (up to 16,000 characters).
        reasoning_effort : {"low", "medium", "high"} or None, optional
            Reasoning level (catalog default ``low``).
        artifact_ids : sequence of str, optional
            Artifacts to attach (bound as ``$artifact`` in proposals).
        model_id : str, optional
            Catalog model id.

        Yields
        ------
        ServerSentEvent
            Turn events in order.

        Raises
        ------
        PaymentRequiredError
            If the wallet cannot cover the hold.
        ConflictError
            If the thread is at its spend cap (code ``session-spend-cap``;
            call :meth:`continue_spend_cap` to raise it).
        """
        return self._http.stream_events(
            "POST",
            ROUTES["chat_turns"].format(session_id=session_id),
            json=_turn_body(message, reasoning_effort, artifact_ids, model_id),
            prefer_bearer=True,
            timeout=_TURN_READ_TIMEOUT,
        )

    async def send(
        self,
        session_id: str,
        message: str,
        *,
        reasoning_effort: ReasoningEffort | None = None,
        artifact_ids: Sequence[str] = (),
        model_id: str = DEFAULT_ASSISTANT_MODEL_ID,
    ) -> ChatTurnResult:
        """Run one turn to completion and return the collected reply.

        Parameters
        ----------
        session_id : str
            Session identifier.
        message : str
            User message (up to 16,000 characters).
        reasoning_effort : {"low", "medium", "high"} or None, optional
            Reasoning level (catalog default ``low``).
        artifact_ids : sequence of str, optional
            Artifacts to attach.
        model_id : str, optional
            Catalog model id.

        Returns
        -------
        ChatTurnResult
            Reply text, spend, tool calls, citations, and proposals.

        Raises
        ------
        CogniChemError
            If the stream ends with an ``error`` event (code
            ``assistant-turn-error``), or on HTTP errors as in :meth:`stream`.
        """
        collector = _TurnCollector()
        async for event in self.stream(
            session_id,
            message,
            reasoning_effort=reasoning_effort,
            artifact_ids=artifact_ids,
            model_id=model_id,
        ):
            collector.add(event)
        return collector.finish()

    async def stop(self, session_id: str, turn_id: str) -> dict[str, str]:
        """Interrupt an in-flight turn; metered tokens bill, the rest releases.

        Parameters
        ----------
        session_id : str
            Session identifier.
        turn_id : str
            Turn identifier (from the ``hold`` event).

        Returns
        -------
        dict
            ``{"status": "stopping", "turn_id": ...}``.
        """
        data = await self._http.request(
            "POST",
            ROUTES["chat_turn_stop"].format(session_id=session_id, turn_id=turn_id),
            prefer_bearer=True,
        )
        assert isinstance(data, dict)
        return data

    async def spend_cap(
        self, session_id: str, *, model_id: str = DEFAULT_ASSISTANT_MODEL_ID
    ) -> ChatSpendCap:
        """Return a thread's Assistant spend and spend cap.

        Parameters
        ----------
        session_id : str
            Session identifier.
        model_id : str, optional
            Catalog model id.

        Returns
        -------
        ChatSpendCap
            Spent, held, cap, and step (USD).
        """
        data = await self._http.request(
            "GET",
            ROUTES["chat_spend_cap"].format(session_id=session_id),
            params={"model_id": model_id},
            prefer_bearer=True,
        )
        return ChatSpendCap.model_validate(data)

    async def continue_spend_cap(
        self,
        session_id: str,
        current_cap_usd: float,
        *,
        model_id: str = DEFAULT_ASSISTANT_MODEL_ID,
    ) -> ChatSpendCap:
        """Raise a thread's spend cap by one step (the user's Continue).

        Parameters
        ----------
        session_id : str
            Session identifier.
        current_cap_usd : float
            The cap you saw. If it has already moved, nothing changes and
            ``raised`` is false.
        model_id : str, optional
            Catalog model id.

        Returns
        -------
        ChatSpendCap
            State after the request.
        """
        data = await self._http.request(
            "POST",
            ROUTES["chat_spend_cap_continue"].format(session_id=session_id),
            json={"current_cap_usd": current_cap_usd, "model_id": model_id},
            prefer_bearer=True,
        )
        return ChatSpendCap.model_validate(data)
