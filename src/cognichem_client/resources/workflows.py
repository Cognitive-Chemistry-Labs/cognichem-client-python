"""Workflow resource clients under ``/workflows`` (validate, estimate, catalog,
runs, and saved definitions)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient, ensure_idempotency_key
from cognichem_client.constants import (
    DEFAULT_WORKFLOW_POLL_INTERVAL,
    DEFAULT_WORKFLOW_TIMEOUT,
    ROUTES,
    WORKFLOW_RUN_STOP_STATUSES,
    WorkflowRunStatus,
)
from cognichem_client.polling import apoll_until, poll_until, run_failure_statuses
from cognichem_client.resources.jobs import _maybe_save
from cognichem_client.types import (
    BinaryResult,
    WorkflowDefinition,
    WorkflowDefinitionList,
    WorkflowDefinitionVersion,
    WorkflowDefinitionVersionList,
    WorkflowEstimate,
    WorkflowNodePorts,
    WorkflowRun,
    WorkflowRunArtifacts,
    WorkflowRunCancelResponse,
    WorkflowRunList,
    WorkflowTemplate,
    WorkflowTemplateSummary,
    WorkflowValidation,
)


def _drop_none(**values: Any) -> dict[str, Any]:
    """Return values without None entries.

    Parameters
    ----------
    **values : any
        Candidate query or body fields.

    Returns
    -------
    dict
        Fields that are set.
    """
    return {k: v for k, v in values.items() if v is not None}


def _spec_body(spec: dict[str, Any], params: dict[str, Any] | None) -> dict[str, Any]:
    """Build a validate / estimate body.

    Parameters
    ----------
    spec : dict
        WorkflowSpec.
    params : dict or None
        Runtime param values.

    Returns
    -------
    dict
        JSON body.
    """
    body: dict[str, Any] = {"spec": spec}
    if params is not None:
        body["params"] = params
    return body


class WorkflowRunsResource:
    """Synchronous workflow run endpoints under ``/workflows/runs``.

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

    def create(
        self,
        run_name: str,
        spec: dict[str, Any],
        *,
        params: dict[str, Any] | None = None,
        max_run_cost: float | None = None,
        definition_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> WorkflowRun:
        """Create (enqueue) a workflow run.

        The server validates the spec, estimates it at the caller's tier, and
        opens a wallet hold before any step starts.

        Parameters
        ----------
        run_name : str
            Unique-per-user run name.
        spec : dict
            WorkflowSpec (frozen on the run).
        params : dict or None, optional
            Runtime param values the spec declares.
        max_run_cost : float or None, optional
            Spend cap; the run pauses instead of exceeding it.
        definition_id : str or None, optional
            Saved definition (``wfd-…``) the spec came from.
        idempotency_key : str or None, optional
            Idempotency key for safe retries. A random key is generated when
            omitted (API-key callers must send one).

        Returns
        -------
        WorkflowRun
            The new run with its step rows and ``estimated_cost``.
        """
        body: dict[str, Any] = {
            "run_name": run_name,
            "spec": spec,
            "params": params or {},
        }
        if max_run_cost is not None:
            body["max_run_cost"] = max_run_cost
        if definition_id is not None:
            body["definition_id"] = definition_id
        data = self._http.request(
            "POST",
            ROUTES["workflows_runs_create"],
            json=body,
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowRun.model_validate(data)

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: WorkflowRunStatus | None = None,
    ) -> WorkflowRunList:
        """List the caller's workflow runs.

        Parameters
        ----------
        limit : int or None, optional
            Page size (1-100).
        offset : int or None, optional
            Page offset.
        status : str or None, optional
            Keep only runs with this status.

        Returns
        -------
        WorkflowRunList
            Page of runs.
        """
        data = self._http.request(
            "GET",
            ROUTES["workflows_runs_list"],
            params=_drop_none(limit=limit, offset=offset, status=status),
        )
        return WorkflowRunList.model_validate(data)

    def get(self, run_id: str, *, include_spec: bool = False) -> WorkflowRun:
        """Fetch a workflow run and its steps.

        Parameters
        ----------
        run_id : str
            Run identifier.
        include_spec : bool, optional
            Also return the frozen ``spec`` and ``definition_id``.

        Returns
        -------
        WorkflowRun
            Run status, costs, and step rows.
        """
        data = self._http.request(
            "GET",
            ROUTES["workflows_runs_get"].format(run_id=run_id),
            params={"include_spec": 1} if include_spec else None,
        )
        return WorkflowRun.model_validate(data)

    def artifacts(self, run_id: str) -> WorkflowRunArtifacts:
        """List artifact ports produced by a workflow run.

        Parameters
        ----------
        run_id : str
            Run identifier.

        Returns
        -------
        WorkflowRunArtifacts
            Artifact ports by step.
        """
        data = self._http.request(
            "GET", ROUTES["workflows_runs_artifacts"].format(run_id=run_id)
        )
        return WorkflowRunArtifacts.model_validate(data)

    def resume(self, run_id: str) -> WorkflowRun:
        """Resume a paused workflow run.

        Parameters
        ----------
        run_id : str
            Run identifier.

        Returns
        -------
        WorkflowRun
            The resumed run.
        """
        data = self._http.request(
            "POST", ROUTES["workflows_runs_resume"].format(run_id=run_id)
        )
        return WorkflowRun.model_validate(data)

    def cancel(self, run_id: str) -> WorkflowRunCancelResponse:
        """Cancel a workflow run and its active step jobs.

        Parameters
        ----------
        run_id : str
            Run identifier.

        Returns
        -------
        WorkflowRunCancelResponse
            Final status and cancelled job ids.
        """
        data = self._http.request(
            "POST", ROUTES["workflows_runs_cancel"].format(run_id=run_id)
        )
        return WorkflowRunCancelResponse.model_validate(data)

    def delete(self, run_id: str) -> None:
        """Delete a workflow run record.

        Artifacts stay in storage (usable as ``$artifact`` inputs until they
        expire) and linked jobs are kept.

        Parameters
        ----------
        run_id : str
            Run identifier.

        Returns
        -------
        None
            The API answers 204 No Content.
        """
        self._http.request(
            "DELETE", ROUTES["workflows_runs_delete"].format(run_id=run_id)
        )

    def wait(
        self,
        run_id: str,
        *,
        poll_interval: float = DEFAULT_WORKFLOW_POLL_INTERVAL,
        timeout: float = DEFAULT_WORKFLOW_TIMEOUT,
        raise_on_failure: bool = False,
    ) -> WorkflowRun:
        """Poll until the run stops: completed, failed, cancelled, or paused.

        A ``paused`` run needs your action (:meth:`resume`, usually after
        raising ``max_run_cost``), so waiting stops there too.

        Parameters
        ----------
        run_id : str
            Run identifier.
        poll_interval : float, optional
            Seconds between polls.
        timeout : float, optional
            Maximum seconds to wait before raising
            :class:`~cognichem_client.errors.PollTimeoutError`.
        raise_on_failure : bool, optional
            When ``True``, raise if the run ends ``failed`` or ``cancelled``.

        Returns
        -------
        WorkflowRun
            The run at its stop status.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses first.
        ProcessFailedError
            If ``raise_on_failure`` is true and the run failed.
        ProcessCancelledError
            If ``raise_on_failure`` is true and the run was cancelled.
        """
        return poll_until(
            lambda: self.get(run_id),
            poll_interval=poll_interval,
            timeout=timeout,
            stop_statuses=WORKFLOW_RUN_STOP_STATUSES,
            subject=lambda run: f"workflow run {run.id}",
            failed_statuses=run_failure_statuses(raise_on_failure),
        )

    def run(
        self,
        run_name: str,
        spec: dict[str, Any],
        *,
        params: dict[str, Any] | None = None,
        max_run_cost: float | None = None,
        definition_id: str | None = None,
        idempotency_key: str | None = None,
        poll_interval: float = DEFAULT_WORKFLOW_POLL_INTERVAL,
        timeout: float = DEFAULT_WORKFLOW_TIMEOUT,
    ) -> WorkflowRun:
        """Create a workflow run and wait until it stops.

        Parameters
        ----------
        run_name : str
            Unique-per-user run name.
        spec : dict
            WorkflowSpec.
        params : dict or None, optional
            Runtime param values.
        max_run_cost : float or None, optional
            Spend cap.
        definition_id : str or None, optional
            Saved definition the spec came from.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).
        poll_interval : float, optional
            Seconds between polls.
        timeout : float, optional
            Maximum seconds to wait.

        Returns
        -------
        WorkflowRun
            The run at ``completed`` or ``paused``. List its outputs with
            :meth:`artifacts`.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses first.
        ProcessFailedError
            If the run fails.
        ProcessCancelledError
            If the run is cancelled.
        """
        created = self.create(
            run_name,
            spec,
            params=params,
            max_run_cost=max_run_cost,
            definition_id=definition_id,
            idempotency_key=idempotency_key,
        )
        return self.wait(
            created.id,
            poll_interval=poll_interval,
            timeout=timeout,
            raise_on_failure=True,
        )


class WorkflowDefinitionsResource:
    """Synchronous saved-definition endpoints under ``/workflows/definitions``.

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

    def create(
        self,
        name: str,
        spec: dict[str, Any],
        *,
        description: str = "",
        graph_layout: dict[str, Any] | None = None,
        spec_version: int = 1,
        idempotency_key: str | None = None,
    ) -> WorkflowDefinition:
        """Save a workflow definition.

        Parameters
        ----------
        name : str
            Unique-per-user name.
        spec : dict
            WorkflowSpec (a top-level ``graph_layout`` moves to its own column).
        description : str, optional
            Description.
        graph_layout : dict or None, optional
            Builder layout (wins over one inside ``spec``).
        spec_version : int, optional
            Spec schema version.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            The saved definition.
        """
        body: dict[str, Any] = {
            "name": name,
            "description": description,
            "spec": spec,
            "spec_version": spec_version,
        }
        if graph_layout is not None:
            body["graph_layout"] = graph_layout
        data = self._http.request(
            "POST",
            ROUTES["workflows_definitions_create"],
            json=body,
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)

    def list(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> WorkflowDefinitionList:
        """List saved definitions (without specs).

        Parameters
        ----------
        limit : int or None, optional
            Page size.
        offset : int or None, optional
            Page offset.

        Returns
        -------
        WorkflowDefinitionList
            Page of definitions.
        """
        data = self._http.request(
            "GET",
            ROUTES["workflows_definitions_list"],
            params=_drop_none(limit=limit, offset=offset),
        )
        return WorkflowDefinitionList.model_validate(data)

    def get(self, definition_id: str) -> WorkflowDefinition:
        """Fetch a saved definition with its spec.

        Parameters
        ----------
        definition_id : str
            Definition identifier (``wfd-…``).

        Returns
        -------
        WorkflowDefinition
            The definition.
        """
        data = self._http.request(
            "GET",
            ROUTES["workflows_definitions_get"].format(definition_id=definition_id),
        )
        return WorkflowDefinition.model_validate(data)

    def update(
        self,
        definition_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        spec: dict[str, Any] | None = None,
        graph_layout: dict[str, Any] | None = None,
        spec_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> WorkflowDefinition:
        """Update a saved definition (only the given fields change).

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        name, description : str or None, optional
            New name or description.
        spec, graph_layout : dict or None, optional
            New spec or builder layout (a spec change adds a version).
        spec_version : int or None, optional
            New spec schema version.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            The updated definition.

        Raises
        ------
        ValueError
            If no field is given.
        """
        body = _drop_none(
            name=name,
            description=description,
            spec=spec,
            graph_layout=graph_layout,
            spec_version=spec_version,
        )
        if not body:
            raise ValueError("Provide at least one field to update")
        data = self._http.request(
            "PATCH",
            ROUTES["workflows_definitions_update"].format(definition_id=definition_id),
            json=body,
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)

    def delete(self, definition_id: str) -> None:
        """Delete a saved definition.

        Parameters
        ----------
        definition_id : str
            Definition identifier.

        Returns
        -------
        None
            The API answers 204 No Content.
        """
        self._http.request(
            "DELETE",
            ROUTES["workflows_definitions_delete"].format(definition_id=definition_id),
        )

    def download(
        self,
        definition_id: str,
        *,
        include_layout: bool = False,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        """Download a definition as WorkflowSpec JSON.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        include_layout : bool, optional
            Merge the builder ``graph_layout`` into the export.
        save_path : str or Path or None, optional
            Optional file or directory path to write the JSON.

        Returns
        -------
        BinaryResult
            JSON bytes plus filename.
        """
        result = self._http.request(
            "GET",
            ROUTES["workflows_definitions_download"].format(
                definition_id=definition_id
            ),
            params={"include_layout": 1} if include_layout else None,
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    def share(
        self, definition_id: str, *, idempotency_key: str | None = None
    ) -> WorkflowDefinition:
        """Turn on link sharing and return the ``share_token``.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            The definition with ``visibility="link"`` and ``share_token``.
        """
        data = self._http.request(
            "POST",
            ROUTES["workflows_definitions_share"].format(definition_id=definition_id),
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)

    def unshare(self, definition_id: str) -> WorkflowDefinition:
        """Revoke link sharing.

        Parameters
        ----------
        definition_id : str
            Definition identifier.

        Returns
        -------
        WorkflowDefinition
            The definition with ``visibility="private"``.
        """
        data = self._http.request(
            "DELETE",
            ROUTES["workflows_definitions_share"].format(definition_id=definition_id),
        )
        return WorkflowDefinition.model_validate(data)

    def get_shared(self, token: str) -> dict[str, Any]:
        """Fetch someone's shared definition export by share token.

        Parameters
        ----------
        token : str
            Share token.

        Returns
        -------
        dict
            Export (spec, plus ``graph_layout`` when present).
        """
        data = self._http.request(
            "GET", ROUTES["workflows_definitions_shared"].format(token=token)
        )
        assert isinstance(data, dict)
        return data

    def fork_shared(
        self,
        token: str,
        name: str,
        *,
        description: str = "",
        idempotency_key: str | None = None,
    ) -> WorkflowDefinition:
        """Copy a shared definition into your library.

        Parameters
        ----------
        token : str
            Share token.
        name : str
            Name for your copy.
        description : str, optional
            Description for your copy.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            Your new definition.
        """
        data = self._http.request(
            "POST",
            ROUTES["workflows_definitions_shared_fork"].format(token=token),
            json={"name": name, "description": description},
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)

    def versions(
        self,
        definition_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> WorkflowDefinitionVersionList:
        """List saved versions of a definition.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        limit : int or None, optional
            Page size.
        offset : int or None, optional
            Page offset.

        Returns
        -------
        WorkflowDefinitionVersionList
            Page of version metadata.
        """
        data = self._http.request(
            "GET",
            ROUTES["workflows_definitions_versions"].format(
                definition_id=definition_id
            ),
            params=_drop_none(limit=limit, offset=offset),
        )
        return WorkflowDefinitionVersionList.model_validate(data)

    def get_version(
        self, definition_id: str, version: int
    ) -> WorkflowDefinitionVersion:
        """Fetch one version snapshot of a definition.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        version : int
            Version number.

        Returns
        -------
        WorkflowDefinitionVersion
            Spec and layout at that version.
        """
        data = self._http.request(
            "GET",
            ROUTES["workflows_definitions_version"].format(
                definition_id=definition_id, version=version
            ),
        )
        return WorkflowDefinitionVersion.model_validate(data)

    def restore_version(
        self,
        definition_id: str,
        version: int,
        *,
        idempotency_key: str | None = None,
    ) -> WorkflowDefinition:
        """Restore a definition to an earlier version.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        version : int
            Version number to restore.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            The definition after the restore.
        """
        data = self._http.request(
            "POST",
            ROUTES["workflows_definitions_version_restore"].format(
                definition_id=definition_id, version=version
            ),
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)


class WorkflowsResource:
    """Synchronous workflow endpoints under ``/workflows``.

    Validate and estimate WorkflowSpecs, browse curated templates and catalog
    ports, and manage runs (:attr:`runs`) and saved definitions
    (:attr:`definitions`).

    Parameters
    ----------
    http : HttpClient
        Shared HTTP transport.

    Attributes
    ----------
    runs : WorkflowRunsResource
        Workflow run endpoints.
    definitions : WorkflowDefinitionsResource
        Saved definition endpoints.
    """

    def __init__(self, http: HttpClient) -> None:
        """Attach the shared HTTP transport and nested resources.

        Parameters
        ----------
        http : HttpClient
            Shared HTTP transport.
        """
        self._http = http
        self.runs = WorkflowRunsResource(http)
        self.definitions = WorkflowDefinitionsResource(http)

    def validate(
        self, spec: dict[str, Any], *, params: dict[str, Any] | None = None
    ) -> WorkflowValidation:
        """Validate a WorkflowSpec without running it.

        An invalid spec is not an error: check ``valid`` and ``errors``.

        Parameters
        ----------
        spec : dict
            WorkflowSpec.
        params : dict or None, optional
            Runtime param values; supply them to check for missing or unknown
            params.

        Returns
        -------
        WorkflowValidation
            Validity, diagnostics, and step order.
        """
        data = self._http.request(
            "POST",
            ROUTES["workflows_validate"],
            json=_spec_body(spec, params),
        )
        return WorkflowValidation.model_validate(data)

    def estimate(
        self, spec: dict[str, Any], *, params: dict[str, Any] | None = None
    ) -> WorkflowEstimate:
        """Estimate the wallet hold for a WorkflowSpec at the caller's tier.

        Same formula as run create; nothing is charged.

        Parameters
        ----------
        spec : dict
            WorkflowSpec.
        params : dict or None, optional
            Runtime param values (scale per-step reservations).

        Returns
        -------
        WorkflowEstimate
            Total, per-step costs, and assumptions.

        Raises
        ------
        ValidationError
            If the spec is invalid (Diagnostic list on ``errors``).
        """
        data = self._http.request(
            "POST",
            ROUTES["workflows_estimate"],
            json=_spec_body(spec, params),
        )
        return WorkflowEstimate.model_validate(data)

    def templates(self) -> list[WorkflowTemplateSummary]:
        """List curated workflow templates in gallery order.

        Returns
        -------
        list of WorkflowTemplateSummary
            Template outlines (fetch a full spec with :meth:`template`).
        """
        data = self._http.request("GET", ROUTES["workflows_templates"])
        return [
            WorkflowTemplateSummary.model_validate(item)
            for item in data.get("templates", [])
        ]

    def template(self, template_id: str) -> WorkflowTemplate:
        """Fetch one curated template with its full WorkflowSpec.

        Parameters
        ----------
        template_id : str
            Template identifier.

        Returns
        -------
        WorkflowTemplate
            Template metadata and ``spec``.
        """
        data = self._http.request(
            "GET", ROUTES["workflows_template"].format(template_id=template_id)
        )
        return WorkflowTemplate.model_validate(data)

    def node_ports(self, job_type: str) -> WorkflowNodePorts:
        """Return the catalog workflow input / output ports of a job type.

        Parameters
        ----------
        job_type : str
            Catalog job type.

        Returns
        -------
        WorkflowNodePorts
            Input and output port definitions.
        """
        data = self._http.request(
            "GET", ROUTES["workflows_node_ports"], params={"job_type": job_type}
        )
        return WorkflowNodePorts.model_validate(data)


class AsyncWorkflowRunsResource:
    """Asynchronous workflow run endpoints under ``/workflows/runs``.

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

    async def create(
        self,
        run_name: str,
        spec: dict[str, Any],
        *,
        params: dict[str, Any] | None = None,
        max_run_cost: float | None = None,
        definition_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> WorkflowRun:
        """Create (enqueue) a workflow run.

        The server validates the spec, estimates it at the caller's tier, and
        opens a wallet hold before any step starts.

        Parameters
        ----------
        run_name : str
            Unique-per-user run name.
        spec : dict
            WorkflowSpec (frozen on the run).
        params : dict or None, optional
            Runtime param values the spec declares.
        max_run_cost : float or None, optional
            Spend cap; the run pauses instead of exceeding it.
        definition_id : str or None, optional
            Saved definition (``wfd-…``) the spec came from.
        idempotency_key : str or None, optional
            Idempotency key for safe retries. A random key is generated when
            omitted (API-key callers must send one).

        Returns
        -------
        WorkflowRun
            The new run with its step rows and ``estimated_cost``.
        """
        body: dict[str, Any] = {
            "run_name": run_name,
            "spec": spec,
            "params": params or {},
        }
        if max_run_cost is not None:
            body["max_run_cost"] = max_run_cost
        if definition_id is not None:
            body["definition_id"] = definition_id
        data = await self._http.request(
            "POST",
            ROUTES["workflows_runs_create"],
            json=body,
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowRun.model_validate(data)

    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: WorkflowRunStatus | None = None,
    ) -> WorkflowRunList:
        """List the caller's workflow runs.

        Parameters
        ----------
        limit : int or None, optional
            Page size (1-100).
        offset : int or None, optional
            Page offset.
        status : str or None, optional
            Keep only runs with this status.

        Returns
        -------
        WorkflowRunList
            Page of runs.
        """
        data = await self._http.request(
            "GET",
            ROUTES["workflows_runs_list"],
            params=_drop_none(limit=limit, offset=offset, status=status),
        )
        return WorkflowRunList.model_validate(data)

    async def get(self, run_id: str, *, include_spec: bool = False) -> WorkflowRun:
        """Fetch a workflow run and its steps.

        Parameters
        ----------
        run_id : str
            Run identifier.
        include_spec : bool, optional
            Also return the frozen ``spec`` and ``definition_id``.

        Returns
        -------
        WorkflowRun
            Run status, costs, and step rows.
        """
        data = await self._http.request(
            "GET",
            ROUTES["workflows_runs_get"].format(run_id=run_id),
            params={"include_spec": 1} if include_spec else None,
        )
        return WorkflowRun.model_validate(data)

    async def artifacts(self, run_id: str) -> WorkflowRunArtifacts:
        """List artifact ports produced by a workflow run.

        Parameters
        ----------
        run_id : str
            Run identifier.

        Returns
        -------
        WorkflowRunArtifacts
            Artifact ports by step.
        """
        data = await self._http.request(
            "GET", ROUTES["workflows_runs_artifacts"].format(run_id=run_id)
        )
        return WorkflowRunArtifacts.model_validate(data)

    async def resume(self, run_id: str) -> WorkflowRun:
        """Resume a paused workflow run.

        Parameters
        ----------
        run_id : str
            Run identifier.

        Returns
        -------
        WorkflowRun
            The resumed run.
        """
        data = await self._http.request(
            "POST", ROUTES["workflows_runs_resume"].format(run_id=run_id)
        )
        return WorkflowRun.model_validate(data)

    async def cancel(self, run_id: str) -> WorkflowRunCancelResponse:
        """Cancel a workflow run and its active step jobs.

        Parameters
        ----------
        run_id : str
            Run identifier.

        Returns
        -------
        WorkflowRunCancelResponse
            Final status and cancelled job ids.
        """
        data = await self._http.request(
            "POST", ROUTES["workflows_runs_cancel"].format(run_id=run_id)
        )
        return WorkflowRunCancelResponse.model_validate(data)

    async def delete(self, run_id: str) -> None:
        """Delete a workflow run record.

        Artifacts stay in storage (usable as ``$artifact`` inputs until they
        expire) and linked jobs are kept.

        Parameters
        ----------
        run_id : str
            Run identifier.

        Returns
        -------
        None
            The API answers 204 No Content.
        """
        await self._http.request(
            "DELETE", ROUTES["workflows_runs_delete"].format(run_id=run_id)
        )

    async def wait(
        self,
        run_id: str,
        *,
        poll_interval: float = DEFAULT_WORKFLOW_POLL_INTERVAL,
        timeout: float = DEFAULT_WORKFLOW_TIMEOUT,
        raise_on_failure: bool = False,
    ) -> WorkflowRun:
        """Poll until the run stops: completed, failed, cancelled, or paused.

        A ``paused`` run needs your action (:meth:`resume`, usually after
        raising ``max_run_cost``), so waiting stops there too.

        Parameters
        ----------
        run_id : str
            Run identifier.
        poll_interval : float, optional
            Seconds between polls.
        timeout : float, optional
            Maximum seconds to wait before raising
            :class:`~cognichem_client.errors.PollTimeoutError`.
        raise_on_failure : bool, optional
            When ``True``, raise if the run ends ``failed`` or ``cancelled``.

        Returns
        -------
        WorkflowRun
            The run at its stop status.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses first.
        ProcessFailedError
            If ``raise_on_failure`` is true and the run failed.
        ProcessCancelledError
            If ``raise_on_failure`` is true and the run was cancelled.
        """
        return await apoll_until(
            lambda: self.get(run_id),
            poll_interval=poll_interval,
            timeout=timeout,
            stop_statuses=WORKFLOW_RUN_STOP_STATUSES,
            subject=lambda run: f"workflow run {run.id}",
            failed_statuses=run_failure_statuses(raise_on_failure),
        )

    async def run(
        self,
        run_name: str,
        spec: dict[str, Any],
        *,
        params: dict[str, Any] | None = None,
        max_run_cost: float | None = None,
        definition_id: str | None = None,
        idempotency_key: str | None = None,
        poll_interval: float = DEFAULT_WORKFLOW_POLL_INTERVAL,
        timeout: float = DEFAULT_WORKFLOW_TIMEOUT,
    ) -> WorkflowRun:
        """Create a workflow run and wait until it stops.

        Parameters
        ----------
        run_name : str
            Unique-per-user run name.
        spec : dict
            WorkflowSpec.
        params : dict or None, optional
            Runtime param values.
        max_run_cost : float or None, optional
            Spend cap.
        definition_id : str or None, optional
            Saved definition the spec came from.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).
        poll_interval : float, optional
            Seconds between polls.
        timeout : float, optional
            Maximum seconds to wait.

        Returns
        -------
        WorkflowRun
            The run at ``completed`` or ``paused``. List its outputs with
            :meth:`artifacts`.

        Raises
        ------
        PollTimeoutError
            If ``timeout`` elapses first.
        ProcessFailedError
            If the run fails.
        ProcessCancelledError
            If the run is cancelled.
        """
        created = await self.create(
            run_name,
            spec,
            params=params,
            max_run_cost=max_run_cost,
            definition_id=definition_id,
            idempotency_key=idempotency_key,
        )
        return await self.wait(
            created.id,
            poll_interval=poll_interval,
            timeout=timeout,
            raise_on_failure=True,
        )


class AsyncWorkflowDefinitionsResource:
    """Asynchronous saved-definition endpoints under ``/workflows/definitions``.

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

    async def create(
        self,
        name: str,
        spec: dict[str, Any],
        *,
        description: str = "",
        graph_layout: dict[str, Any] | None = None,
        spec_version: int = 1,
        idempotency_key: str | None = None,
    ) -> WorkflowDefinition:
        """Save a workflow definition.

        Parameters
        ----------
        name : str
            Unique-per-user name.
        spec : dict
            WorkflowSpec (a top-level ``graph_layout`` moves to its own column).
        description : str, optional
            Description.
        graph_layout : dict or None, optional
            Builder layout (wins over one inside ``spec``).
        spec_version : int, optional
            Spec schema version.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            The saved definition.
        """
        body: dict[str, Any] = {
            "name": name,
            "description": description,
            "spec": spec,
            "spec_version": spec_version,
        }
        if graph_layout is not None:
            body["graph_layout"] = graph_layout
        data = await self._http.request(
            "POST",
            ROUTES["workflows_definitions_create"],
            json=body,
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)

    async def list(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> WorkflowDefinitionList:
        """List saved definitions (without specs).

        Parameters
        ----------
        limit : int or None, optional
            Page size.
        offset : int or None, optional
            Page offset.

        Returns
        -------
        WorkflowDefinitionList
            Page of definitions.
        """
        data = await self._http.request(
            "GET",
            ROUTES["workflows_definitions_list"],
            params=_drop_none(limit=limit, offset=offset),
        )
        return WorkflowDefinitionList.model_validate(data)

    async def get(self, definition_id: str) -> WorkflowDefinition:
        """Fetch a saved definition with its spec.

        Parameters
        ----------
        definition_id : str
            Definition identifier (``wfd-…``).

        Returns
        -------
        WorkflowDefinition
            The definition.
        """
        data = await self._http.request(
            "GET",
            ROUTES["workflows_definitions_get"].format(definition_id=definition_id),
        )
        return WorkflowDefinition.model_validate(data)

    async def update(
        self,
        definition_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        spec: dict[str, Any] | None = None,
        graph_layout: dict[str, Any] | None = None,
        spec_version: int | None = None,
        idempotency_key: str | None = None,
    ) -> WorkflowDefinition:
        """Update a saved definition (only the given fields change).

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        name, description : str or None, optional
            New name or description.
        spec, graph_layout : dict or None, optional
            New spec or builder layout (a spec change adds a version).
        spec_version : int or None, optional
            New spec schema version.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            The updated definition.

        Raises
        ------
        ValueError
            If no field is given.
        """
        body = _drop_none(
            name=name,
            description=description,
            spec=spec,
            graph_layout=graph_layout,
            spec_version=spec_version,
        )
        if not body:
            raise ValueError("Provide at least one field to update")
        data = await self._http.request(
            "PATCH",
            ROUTES["workflows_definitions_update"].format(definition_id=definition_id),
            json=body,
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)

    async def delete(self, definition_id: str) -> None:
        """Delete a saved definition.

        Parameters
        ----------
        definition_id : str
            Definition identifier.

        Returns
        -------
        None
            The API answers 204 No Content.
        """
        await self._http.request(
            "DELETE",
            ROUTES["workflows_definitions_delete"].format(definition_id=definition_id),
        )

    async def download(
        self,
        definition_id: str,
        *,
        include_layout: bool = False,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        """Download a definition as WorkflowSpec JSON.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        include_layout : bool, optional
            Merge the builder ``graph_layout`` into the export.
        save_path : str or Path or None, optional
            Optional file or directory path to write the JSON.

        Returns
        -------
        BinaryResult
            JSON bytes plus filename.
        """
        result = await self._http.request(
            "GET",
            ROUTES["workflows_definitions_download"].format(
                definition_id=definition_id
            ),
            params={"include_layout": 1} if include_layout else None,
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    async def share(
        self, definition_id: str, *, idempotency_key: str | None = None
    ) -> WorkflowDefinition:
        """Turn on link sharing and return the ``share_token``.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            The definition with ``visibility="link"`` and ``share_token``.
        """
        data = await self._http.request(
            "POST",
            ROUTES["workflows_definitions_share"].format(definition_id=definition_id),
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)

    async def unshare(self, definition_id: str) -> WorkflowDefinition:
        """Revoke link sharing.

        Parameters
        ----------
        definition_id : str
            Definition identifier.

        Returns
        -------
        WorkflowDefinition
            The definition with ``visibility="private"``.
        """
        data = await self._http.request(
            "DELETE",
            ROUTES["workflows_definitions_share"].format(definition_id=definition_id),
        )
        return WorkflowDefinition.model_validate(data)

    async def get_shared(self, token: str) -> dict[str, Any]:
        """Fetch someone's shared definition export by share token.

        Parameters
        ----------
        token : str
            Share token.

        Returns
        -------
        dict
            Export (spec, plus ``graph_layout`` when present).
        """
        data = await self._http.request(
            "GET", ROUTES["workflows_definitions_shared"].format(token=token)
        )
        assert isinstance(data, dict)
        return data

    async def fork_shared(
        self,
        token: str,
        name: str,
        *,
        description: str = "",
        idempotency_key: str | None = None,
    ) -> WorkflowDefinition:
        """Copy a shared definition into your library.

        Parameters
        ----------
        token : str
            Share token.
        name : str
            Name for your copy.
        description : str, optional
            Description for your copy.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            Your new definition.
        """
        data = await self._http.request(
            "POST",
            ROUTES["workflows_definitions_shared_fork"].format(token=token),
            json={"name": name, "description": description},
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)

    async def versions(
        self,
        definition_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> WorkflowDefinitionVersionList:
        """List saved versions of a definition.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        limit : int or None, optional
            Page size.
        offset : int or None, optional
            Page offset.

        Returns
        -------
        WorkflowDefinitionVersionList
            Page of version metadata.
        """
        data = await self._http.request(
            "GET",
            ROUTES["workflows_definitions_versions"].format(
                definition_id=definition_id
            ),
            params=_drop_none(limit=limit, offset=offset),
        )
        return WorkflowDefinitionVersionList.model_validate(data)

    async def get_version(
        self, definition_id: str, version: int
    ) -> WorkflowDefinitionVersion:
        """Fetch one version snapshot of a definition.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        version : int
            Version number.

        Returns
        -------
        WorkflowDefinitionVersion
            Spec and layout at that version.
        """
        data = await self._http.request(
            "GET",
            ROUTES["workflows_definitions_version"].format(
                definition_id=definition_id, version=version
            ),
        )
        return WorkflowDefinitionVersion.model_validate(data)

    async def restore_version(
        self,
        definition_id: str,
        version: int,
        *,
        idempotency_key: str | None = None,
    ) -> WorkflowDefinition:
        """Restore a definition to an earlier version.

        Parameters
        ----------
        definition_id : str
            Definition identifier.
        version : int
            Version number to restore.
        idempotency_key : str or None, optional
            Idempotency key for safe retries (generated when omitted).

        Returns
        -------
        WorkflowDefinition
            The definition after the restore.
        """
        data = await self._http.request(
            "POST",
            ROUTES["workflows_definitions_version_restore"].format(
                definition_id=definition_id, version=version
            ),
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return WorkflowDefinition.model_validate(data)


class AsyncWorkflowsResource:
    """Asynchronous workflow endpoints under ``/workflows``.

    Validate and estimate WorkflowSpecs, browse curated templates and catalog
    ports, and manage runs (:attr:`runs`) and saved definitions
    (:attr:`definitions`).

    Parameters
    ----------
    http : AsyncHttpClient
        Shared async HTTP transport.

    Attributes
    ----------
    runs : AsyncWorkflowRunsResource
        Workflow run endpoints.
    definitions : AsyncWorkflowDefinitionsResource
        Saved definition endpoints.
    """

    def __init__(self, http: AsyncHttpClient) -> None:
        """Attach the shared async HTTP transport and nested resources.

        Parameters
        ----------
        http : AsyncHttpClient
            Shared async HTTP transport.
        """
        self._http = http
        self.runs = AsyncWorkflowRunsResource(http)
        self.definitions = AsyncWorkflowDefinitionsResource(http)

    async def validate(
        self, spec: dict[str, Any], *, params: dict[str, Any] | None = None
    ) -> WorkflowValidation:
        """Validate a WorkflowSpec without running it.

        An invalid spec is not an error: check ``valid`` and ``errors``.

        Parameters
        ----------
        spec : dict
            WorkflowSpec.
        params : dict or None, optional
            Runtime param values; supply them to check for missing or unknown
            params.

        Returns
        -------
        WorkflowValidation
            Validity, diagnostics, and step order.
        """
        data = await self._http.request(
            "POST",
            ROUTES["workflows_validate"],
            json=_spec_body(spec, params),
        )
        return WorkflowValidation.model_validate(data)

    async def estimate(
        self, spec: dict[str, Any], *, params: dict[str, Any] | None = None
    ) -> WorkflowEstimate:
        """Estimate the wallet hold for a WorkflowSpec at the caller's tier.

        Same formula as run create; nothing is charged.

        Parameters
        ----------
        spec : dict
            WorkflowSpec.
        params : dict or None, optional
            Runtime param values (scale per-step reservations).

        Returns
        -------
        WorkflowEstimate
            Total, per-step costs, and assumptions.

        Raises
        ------
        ValidationError
            If the spec is invalid (Diagnostic list on ``errors``).
        """
        data = await self._http.request(
            "POST",
            ROUTES["workflows_estimate"],
            json=_spec_body(spec, params),
        )
        return WorkflowEstimate.model_validate(data)

    async def templates(self) -> list[WorkflowTemplateSummary]:
        """List curated workflow templates in gallery order.

        Returns
        -------
        list of WorkflowTemplateSummary
            Template outlines (fetch a full spec with :meth:`template`).
        """
        data = await self._http.request("GET", ROUTES["workflows_templates"])
        return [
            WorkflowTemplateSummary.model_validate(item)
            for item in data.get("templates", [])
        ]

    async def template(self, template_id: str) -> WorkflowTemplate:
        """Fetch one curated template with its full WorkflowSpec.

        Parameters
        ----------
        template_id : str
            Template identifier.

        Returns
        -------
        WorkflowTemplate
            Template metadata and ``spec``.
        """
        data = await self._http.request(
            "GET", ROUTES["workflows_template"].format(template_id=template_id)
        )
        return WorkflowTemplate.model_validate(data)

    async def node_ports(self, job_type: str) -> WorkflowNodePorts:
        """Return the catalog workflow input / output ports of a job type.

        Parameters
        ----------
        job_type : str
            Catalog job type.

        Returns
        -------
        WorkflowNodePorts
            Input and output port definitions.
        """
        data = await self._http.request(
            "GET", ROUTES["workflows_node_ports"], params={"job_type": job_type}
        )
        return WorkflowNodePorts.model_validate(data)
