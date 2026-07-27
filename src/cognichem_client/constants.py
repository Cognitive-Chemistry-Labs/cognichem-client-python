"""Route map and catalog constants mirrored from the CogniChem API contract.

Attributes
----------
DEFAULT_BASE_URL : str
    Default API origin used by sync and async clients.
API_V1_STR : str
    Versioned API path prefix (``/api/v1``).
ROUTES : dict of str to str
    Named endpoint path map mirroring back-end ``Settings.ROUTE_MAP``.
JobType : typing.Literal
    Allowed long-running job type string literals.
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
DEFAULT_HTTP_TIMEOUT : float
    Default per-request HTTP timeout in seconds.
"""

from __future__ import annotations

from typing import Final, Literal

DEFAULT_BASE_URL: Final = "https://api.cognichem.com"
API_V1_STR: Final = "/api/v1"

# Mirrors apps/back-end-api Settings.ROUTE_MAP
ROUTES: Final[dict[str, str]] = {
    "auth_login_email": f"{API_V1_STR}/auth/login-email",
    "auth_check": f"{API_V1_STR}/auth/check",
    "auth_refresh": f"{API_V1_STR}/auth/refresh",
    "auth_logout": f"{API_V1_STR}/auth/logout",
    "auth_api_keys": f"{API_V1_STR}/auth/api-keys",
    "auth_api_keys_item": f"{API_V1_STR}/auth/api-keys/{{key_id}}",
    "auth_api_keys_rotate": f"{API_V1_STR}/auth/api-keys/{{key_id}}/rotate",
    "jobs_submit": f"{API_V1_STR}/jobs/submit",
    "jobs_submit_multiple": f"{API_V1_STR}/jobs/submit-multiple",
    "jobs_info": f"{API_V1_STR}/jobs/info",
    "jobs_list": f"{API_V1_STR}/jobs/list",
    "jobs_status": f"{API_V1_STR}/jobs/status",
    "jobs_result": f"{API_V1_STR}/jobs/result",
    "jobs_result_multiple": f"{API_V1_STR}/jobs/result-multiple",
    "jobs_cancel": f"{API_V1_STR}/jobs/cancel",
    "jobs_delete": f"{API_V1_STR}/jobs/delete",
    "inference_submit": f"{API_V1_STR}/inference/submit",
    "inference_submit_batch": f"{API_V1_STR}/inference/submit-batch",
    "inference_list": f"{API_V1_STR}/inference/list",
    "inference_status": f"{API_V1_STR}/inference/status",
    "inference_result": f"{API_V1_STR}/inference/result",
    "inference_delete": f"{API_V1_STR}/inference/delete",
    "mpnn_user_models": f"{API_V1_STR}/user-models/mpnn",
    "mpnn_public_models": f"{API_V1_STR}/public-models/mpnn",
    "utils_submit": f"{API_V1_STR}/utils/submit",
    "utils_list": f"{API_V1_STR}/utils/list",
    "utils_status": f"{API_V1_STR}/utils/status",
    "utils_result": f"{API_V1_STR}/utils/result",
    "utils_delete": f"{API_V1_STR}/utils/delete",
    "usage_limits": f"{API_V1_STR}/usage-limits",
}

JobType = Literal[
    "autodockvina",
    "boltz2",
    "boltzgen",
    "cantera",
    "convert-batch",
    "diffdock",
    "drugflow",
    "esmfold2",
    "evo2",
    "freewilson",
    "gnina",
    "molecule-rmsd-matrix",
    "opendde",
    "openmm-md",
    "padel-descriptor",
    "rfantibody-finetune",
    "rfantibody-pipeline",
    "rfantibody-proteinmpnn",
    "rfantibody-rfdiffusion",
    "rfantibody-tcr-predict",
    "surfmap",
    "thompsonsampling",
    "train-mpnn",
]

JOB_TYPES: Final[frozenset[str]] = frozenset(
    {
        "autodockvina",
        "boltz2",
        "boltzgen",
        "cantera",
        "convert-batch",
        "diffdock",
        "drugflow",
        "esmfold2",
        "evo2",
        "freewilson",
        "gnina",
        "molecule-rmsd-matrix",
        "opendde",
        "openmm-md",
        "padel-descriptor",
        "rfantibody-finetune",
        "rfantibody-pipeline",
        "rfantibody-proteinmpnn",
        "rfantibody-rfdiffusion",
        "rfantibody-tcr-predict",
        "surfmap",
        "thompsonsampling",
        "train-mpnn",
    }
)

UtilityType = Literal["convert", "molecule_rmsd"]
UTILITY_TYPES: Final[frozenset[str]] = frozenset({"convert", "molecule_rmsd"})

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

DEFAULT_JOB_POLL_INTERVAL: Final = 5.0
DEFAULT_JOB_TIMEOUT: Final = 3600.0
DEFAULT_FAST_POLL_INTERVAL: Final = 0.3
DEFAULT_FAST_TIMEOUT: Final = 300.0
DEFAULT_HTTP_TIMEOUT: Final = 60.0
