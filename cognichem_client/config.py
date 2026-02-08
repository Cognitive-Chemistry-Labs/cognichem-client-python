# The configuration constants defined in this file are used throughout the
# client implementation to construct API request URLs and manage interactions
# with the CogniChem API.

# The constants defined in this file include:
# - HOSTNAME: The base URL for the CogniChem API.
# - API_V1_STR: The version string for the API endpoints.
# - ROUTE_MAP: A dictionary mapping endpoint names to their respective URL
#   paths.

HOSTNAME = "https://api.cognichem.com"
API_V1_STR = "/api/v1"
ROUTE_MAP = {
    "auth_check": f"{API_V1_STR}/auth/check",

    "job_submit": f"{API_V1_STR}/jobs/submit",
    "job_list": f"{API_V1_STR}/jobs/list",
    "job_status": f"{API_V1_STR}/jobs/status",
    "job_cancel": f"{API_V1_STR}/jobs/cancel",
    "job_delete": f"{API_V1_STR}/jobs/delete",
    "job_result": f"{API_V1_STR}/jobs/result",

    "inference_submit": f"{API_V1_STR}/inference/submit",
    "inference_list": f"{API_V1_STR}/inference/list",
    "inference_status": f"{API_V1_STR}/inference/status",
    "inference_result": f"{API_V1_STR}/inference/result",
    "inference_delete": f"{API_V1_STR}/inference/delete",

    "public_models_mpnn": f"{API_V1_STR}/public-models/mpnn",
    "user_models_mpnn": f"{API_V1_STR}/user-models/mpnn",

    "utils_submit": f"{API_V1_STR}/utils/submit",
    "utils_list": f"{API_V1_STR}/utils/list",
    "utils_status": f"{API_V1_STR}/utils/status",
    "utils_result": f"{API_V1_STR}/utils/result",
    "utils_delete": f"{API_V1_STR}/utils/delete",
}