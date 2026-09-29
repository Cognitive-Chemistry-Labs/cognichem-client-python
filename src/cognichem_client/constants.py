"""Route map and catalog constants mirrored from the CogniChem API contract.

Attributes
----------
DEFAULT_BASE_URL : str
    Default API origin used by sync and async clients.
API_V1_STR : str
    Versioned API path prefix (``/api/v1``).
ROUTES : dict of str to str
    Named endpoint path map mirroring back-end ``Settings.ROUTE_MAP``, plus
    routes that map does not list.
JobType : typing.Literal
    Allowed long-running job type string literals (catalog job types that can
    be submitted on their own).
JOB_TYPES : frozenset of str
    Runtime set of supported job type strings.
UtilityType : typing.Literal
    Allowed utility type string literals.
UTILITY_TYPES : frozenset of str
    Runtime set of supported utility type strings.
ModelType : typing.Literal
    Allowed inference model family string literals.
MODEL_TYPES : frozenset of str
    Runtime set of supported model type strings.
Resource : typing.Literal
    Allowed compute resource tier string literals.
RESOURCES : frozenset of str
    Runtime set of supported resource tier strings.
WorkflowRunStatus : typing.Literal
    Workflow run status string literals.
WORKFLOW_RUN_STATUSES : frozenset of str
    Runtime set of workflow run statuses.
WORKFLOW_RUN_STOP_STATUSES : frozenset of str
    Statuses where :meth:`WorkflowRunsResource.wait` stops polling
    (``completed``, ``failed``, ``cancelled``, ``paused``).
ReferencePaperSet : typing.Literal
    Reference-KG paper sets (``method``, ``used_cognichem``, ``general``).
ReferenceEdgeKind : typing.Literal
    Reference-KG edge kinds.
EventKind : typing.Literal
    Completion event subject kinds (``job``, ``workflow_run``).
ReasoningEffort : typing.Literal
    CogniChem Assistant reasoning levels.
DEFAULT_ASSISTANT_MODEL_ID : str
    Catalog model id of the CogniChem Assistant.
JOB_TERMINAL_STATUSES : frozenset of str
    Terminal statuses for long-running jobs (``completed``, ``error``,
    ``cancelled``).
POLLABLE_TERMINAL_STATUSES : frozenset of str
    Default terminal statuses used by shared polling helpers.
DEFAULT_JOB_POLL_INTERVAL : float
    Default seconds between job status polls.
DEFAULT_JOB_TIMEOUT : float
    Default maximum seconds to wait for a job to finish.
DEFAULT_FAST_POLL_INTERVAL : float
    Default seconds between inference/utility status polls.
DEFAULT_FAST_TIMEOUT : float
    Default maximum seconds to wait for inference/utility completion.
DEFAULT_WORKFLOW_POLL_INTERVAL : float
    Default seconds between workflow run polls.
DEFAULT_WORKFLOW_TIMEOUT : float
    Default maximum seconds to wait for a workflow run to stop.
MAX_EVENTS_WAIT : float
    Longest ``wait`` (seconds) ``GET /events`` accepts.
DEFAULT_HTTP_TIMEOUT : float
    Default per-request HTTP timeout in seconds.
"""

from __future__ import annotations

from typing import Final, Literal

DEFAULT_BASE_URL: Final = "https://api.cognichem.com"
API_V1_STR: Final = "/api/v1"

# Mirrors apps/back-end-api Settings.ROUTE_MAP (plus routes it does not list:
# health/ready, templates, node-ports, definition share/versions, lookup,
# reference, and wallet).
ROUTES: Final[dict[str, str]] = {
    "health": "/health",
    "ready": "/ready",
    "auth_login_email": f"{API_V1_STR}/auth/login-email",
    "auth_check": f"{API_V1_STR}/auth/check",
    "auth_refresh": f"{API_V1_STR}/auth/refresh",
    "auth_logout": f"{API_V1_STR}/auth/logout",
    "auth_api_keys": f"{API_V1_STR}/auth/api-keys",
    "auth_api_keys_item": f"{API_V1_STR}/auth/api-keys/{{key_id}}",
    "auth_api_keys_rotate": f"{API_V1_STR}/auth/api-keys/{{key_id}}/rotate",
    "jobs_submit": f"{API_V1_STR}/jobs/submit",
    "jobs_submit_multiple": f"{API_V1_STR}/jobs/submit-multiple",
    "jobs_estimate": f"{API_V1_STR}/jobs/estimate",
    "jobs_info": f"{API_V1_STR}/jobs/info",
    "jobs_list": f"{API_V1_STR}/jobs/list",
    "jobs_status": f"{API_V1_STR}/jobs/status",
    "jobs_result": f"{API_V1_STR}/jobs/result",
    "jobs_result_multiple": f"{API_V1_STR}/jobs/result-multiple",
    "jobs_cancel": f"{API_V1_STR}/jobs/cancel",
    "jobs_delete": f"{API_V1_STR}/jobs/delete",
    "artifacts_list": f"{API_V1_STR}/artifacts",
    "artifacts_upload": f"{API_V1_STR}/artifacts",
    "artifacts_usage": f"{API_V1_STR}/artifacts/usage",
    "artifacts_get": f"{API_V1_STR}/artifacts/{{artifact_id}}",
    "artifacts_download": f"{API_V1_STR}/artifacts/{{artifact_id}}/download",
    "artifacts_download_record": f"{API_V1_STR}/artifacts/{{artifact_id}}/download",
    "artifacts_delete": f"{API_V1_STR}/artifacts/{{artifact_id}}",
    "workflows_validate": f"{API_V1_STR}/workflows/validate",
    "workflows_estimate": f"{API_V1_STR}/workflows/estimate",
    "workflows_templates": f"{API_V1_STR}/workflows/templates",
    "workflows_template": f"{API_V1_STR}/workflows/templates/{{template_id}}",
    "workflows_node_ports": f"{API_V1_STR}/workflows/node-ports",
    "workflows_definitions_create": f"{API_V1_STR}/workflows/definitions",
    "workflows_definitions_list": f"{API_V1_STR}/workflows/definitions",
    "workflows_definitions_get": (
        f"{API_V1_STR}/workflows/definitions/{{definition_id}}"
    ),
    "workflows_definitions_update": (
        f"{API_V1_STR}/workflows/definitions/{{definition_id}}"
    ),
    "workflows_definitions_delete": (
        f"{API_V1_STR}/workflows/definitions/{{definition_id}}"
    ),
    "workflows_definitions_download": (
        f"{API_V1_STR}/workflows/definitions/{{definition_id}}/download"
    ),
    "workflows_definitions_share": (
        f"{API_V1_STR}/workflows/definitions/{{definition_id}}/share"
    ),
    "workflows_definitions_versions": (
        f"{API_V1_STR}/workflows/definitions/{{definition_id}}/versions"
    ),
    "workflows_definitions_version": (
        f"{API_V1_STR}/workflows/definitions/{{definition_id}}/versions/{{version}}"
    ),
    "workflows_definitions_version_restore": (
        f"{API_V1_STR}/workflows/definitions/{{definition_id}}/versions/{{version}}/restore"
    ),
    "workflows_definitions_shared": (
        f"{API_V1_STR}/workflows/definitions/shared/{{token}}"
    ),
    "workflows_definitions_shared_fork": (
        f"{API_V1_STR}/workflows/definitions/shared/{{token}}/fork"
    ),
    "workflows_runs_create": f"{API_V1_STR}/workflows/runs",
    "workflows_runs_list": f"{API_V1_STR}/workflows/runs",
    "workflows_runs_get": f"{API_V1_STR}/workflows/runs/{{run_id}}",
    "workflows_runs_artifacts": f"{API_V1_STR}/workflows/runs/{{run_id}}/artifacts",
    "workflows_runs_resume": f"{API_V1_STR}/workflows/runs/{{run_id}}/resume",
    "workflows_runs_cancel": f"{API_V1_STR}/workflows/runs/{{run_id}}/cancel",
    "workflows_runs_delete": f"{API_V1_STR}/workflows/runs/{{run_id}}",
    "inference_submit": f"{API_V1_STR}/inference/submit",
    "inference_submit_batch": f"{API_V1_STR}/inference/submit-batch",
    "inference_list": f"{API_V1_STR}/inference/list",
    "inference_status": f"{API_V1_STR}/inference/status",
    "inference_result": f"{API_V1_STR}/inference/result",
    "inference_delete": f"{API_V1_STR}/inference/delete",
    "inference_cancel": f"{API_V1_STR}/inference/cancel",
    "mpnn_user_models": f"{API_V1_STR}/user-models/mpnn",
    "mpnn_public_models": f"{API_V1_STR}/public-models/mpnn",
    "utils_submit": f"{API_V1_STR}/utils/submit",
    "utils_list": f"{API_V1_STR}/utils/list",
    "utils_status": f"{API_V1_STR}/utils/status",
    "utils_result": f"{API_V1_STR}/utils/result",
    "utils_delete": f"{API_V1_STR}/utils/delete",
    "utils_cancel": f"{API_V1_STR}/utils/cancel",
    "usage_limits": f"{API_V1_STR}/usage-limits",
    "wallet": f"{API_V1_STR}/wallet",
    "events": f"{API_V1_STR}/events",
    "lookup_pubchem": f"{API_V1_STR}/lookup/pubchem",
    "lookup_chembl": f"{API_V1_STR}/lookup/chembl",
    "lookup_targets": f"{API_V1_STR}/lookup/targets",
    "lookup_uniprot": f"{API_V1_STR}/lookup/uniprot",
    "lookup_pdb": f"{API_V1_STR}/lookup/pdb",
    "lookup_properties": f"{API_V1_STR}/lookup/properties",
    "reference_papers": f"{API_V1_STR}/reference/papers",
    "reference_paper": f"{API_V1_STR}/reference/papers/{{paper_id}}",
    "reference_neighborhood": f"{API_V1_STR}/reference/neighborhood",
    "chat_sessions": f"{API_V1_STR}/chat/sessions",
    "chat_session": f"{API_V1_STR}/chat/sessions/{{session_id}}",
    "chat_messages": f"{API_V1_STR}/chat/sessions/{{session_id}}/messages",
    "chat_estimate": f"{API_V1_STR}/chat/sessions/{{session_id}}/estimate",
    "chat_turns": f"{API_V1_STR}/chat/sessions/{{session_id}}/turns",
    "chat_turn_stop": (
        f"{API_V1_STR}/chat/sessions/{{session_id}}/turns/{{turn_id}}/stop"
    ),
    "chat_spend_cap": f"{API_V1_STR}/chat/sessions/{{session_id}}/spend-cap",
    "chat_spend_cap_continue": (
        f"{API_V1_STR}/chat/sessions/{{session_id}}/spend-cap/continue"
    ),
    "chat_proposals": f"{API_V1_STR}/chat/sessions/{{session_id}}/proposals",
    "chat_proposal": (
        f"{API_V1_STR}/chat/sessions/{{session_id}}/proposals/{{proposal_id}}"
    ),
    "chat_proposal_approve": (
        f"{API_V1_STR}/chat/sessions/{{session_id}}/proposals/{{proposal_id}}/approve"
    ),
    "chat_proposal_reject": (
        f"{API_V1_STR}/chat/sessions/{{session_id}}/proposals/{{proposal_id}}/reject"
    ),
}

# Mirrors packages/job-catalog JOB_TYPES minus workflow-only helpers
# (``workflow-adapter`` / ``workflow-filter``).
JobType = Literal[
    "admet-predict",
    "autodockvina",
    "boltz2",
    "boltzgen",
    "cantera",
    "conformer-ensemble",
    "convert-batch",
    "coolprop",
    "diffdock",
    "drugflow",
    "druglikeness-filter",
    "esmfold2",
    "evo2",
    "fingerprint-cluster",
    "freebindcraft",
    "freewilson",
    "gnina",
    "group-contribution",
    "md-analyze",
    "mm-gbsa",
    "mmp-analysis",
    "molecule-rmsd-matrix",
    "molecule-standardize",
    "nasa-thermo-fit",
    "opendde",
    "openmm-md",
    "padel-descriptor",
    "phreeqc",
    "plip-profile",
    "pocket-detect",
    "protein-prepare",
    "reaction-enumerate",
    "retrosynthesis",
    "rfantibody-finetune",
    "rfantibody-pipeline",
    "rfantibody-proteinmpnn",
    "rfantibody-rfdiffusion",
    "rfantibody-tcr-predict",
    "rmg-mechanism",
    "scaffold-analyze",
    "surfdock",
    "surfmap",
    "thompsonsampling",
    "train-mpnn",
    "vle-flash",
]

JOB_TYPES: Final[frozenset[str]] = frozenset(
    {
        "admet-predict",
        "autodockvina",
        "boltz2",
        "boltzgen",
        "cantera",
        "conformer-ensemble",
        "convert-batch",
        "coolprop",
        "diffdock",
        "drugflow",
        "druglikeness-filter",
        "esmfold2",
        "evo2",
        "fingerprint-cluster",
        "freebindcraft",
        "freewilson",
        "gnina",
        "group-contribution",
        "md-analyze",
        "mm-gbsa",
        "mmp-analysis",
        "molecule-rmsd-matrix",
        "molecule-standardize",
        "nasa-thermo-fit",
        "opendde",
        "openmm-md",
        "padel-descriptor",
        "phreeqc",
        "plip-profile",
        "pocket-detect",
        "protein-prepare",
        "reaction-enumerate",
        "retrosynthesis",
        "rfantibody-finetune",
        "rfantibody-pipeline",
        "rfantibody-proteinmpnn",
        "rfantibody-rfdiffusion",
        "rfantibody-tcr-predict",
        "rmg-mechanism",
        "scaffold-analyze",
        "surfdock",
        "surfmap",
        "thompsonsampling",
        "train-mpnn",
        "vle-flash",
    }
)

UtilityType = Literal[
    "convert",
    "molecule_rmsd",
    "molecule_standardize",
    "druglikeness_filter",
    "coolprop",
]

UTILITY_TYPES: Final[frozenset[str]] = frozenset(
    {
        "convert",
        "molecule_rmsd",
        "molecule_standardize",
        "druglikeness_filter",
        "coolprop",
    }
)

ModelType = Literal["mpnn"]
MODEL_TYPES: Final[frozenset[str]] = frozenset({"mpnn"})

Resource = Literal[
    "default",
    "cpu",
    "t4",
    "l4",
    "a10",
    "l40s",
    "a100-40gb",
    "a100-80gb",
    "h100",
    "h200",
    "b200",
]

RESOURCES: Final[frozenset[str]] = frozenset(
    {
        "default",
        "cpu",
        "t4",
        "l4",
        "a10",
        "l40s",
        "a100-40gb",
        "a100-80gb",
        "h100",
        "h200",
        "b200",
    }
)

# Mirrors cognichem-jobs-domain TERMINAL_STATUSES
JOB_TERMINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {"completed", "error", "cancelled"}
)
# Modal-polled inference/utils typically use completed|error
POLLABLE_TERMINAL_STATUSES: Final[frozenset[str]] = frozenset(
    {"completed", "error", "cancelled"}
)

WorkflowRunStatus = Literal[
    "pending", "running", "paused", "completed", "failed", "cancelled"
]
WORKFLOW_RUN_STATUSES: Final[frozenset[str]] = frozenset(
    {"pending", "running", "paused", "completed", "failed", "cancelled"}
)
# ``paused`` needs a user action (resume or a higher ``max_run_cost``), so
# waiting stops there too (mirrors cognichem-mcp WORKFLOW_RUN_STOP_STATUSES).
WORKFLOW_RUN_STOP_STATUSES: Final[frozenset[str]] = frozenset(
    {"completed", "failed", "cancelled", "paused"}
)

ReferencePaperSet = Literal["method", "used_cognichem", "general"]
ReferenceEdgeKind = Literal["cites", "method_of", "uses_tool", "compares", "describes"]
EventKind = Literal["job", "workflow_run"]
ReasoningEffort = Literal["low", "medium", "high"]

DEFAULT_ASSISTANT_MODEL_ID: Final = "cognichem-assistant"

DEFAULT_JOB_POLL_INTERVAL: Final = 5.0
DEFAULT_JOB_TIMEOUT: Final = 3600.0
DEFAULT_FAST_POLL_INTERVAL: Final = 0.3
DEFAULT_FAST_TIMEOUT: Final = 300.0
DEFAULT_WORKFLOW_POLL_INTERVAL: Final = 10.0
DEFAULT_WORKFLOW_TIMEOUT: Final = 6 * 3600.0
MAX_EVENTS_WAIT: Final = 25.0
DEFAULT_HTTP_TIMEOUT: Final = 60.0
