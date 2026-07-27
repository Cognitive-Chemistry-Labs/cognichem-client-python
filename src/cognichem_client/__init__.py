"""Public package entry for the CogniChem Python client.

Re-exports the sync and async clients, common response types, catalog
constants, and exception classes used by application code.
"""

from cognichem_client.async_client import AsyncCogniChem
from cognichem_client.client import CogniChem
from cognichem_client.constants import (
    JOB_TERMINAL_STATUSES,
    JOB_TYPES,
    MODEL_TYPES,
    RESOURCES,
    UTILITY_TYPES,
)
from cognichem_client.errors import (
    AuthenticationError,
    CogniChemError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PollTimeoutError,
    ProcessCancelledError,
    ProcessFailedError,
    RateLimitError,
    ValidationError,
)
from cognichem_client.types import (
    BinaryResult,
    DataResult,
    JobSubmitRequest,
    ProcessStatus,
)

__all__ = [
    "AsyncCogniChem",
    "AuthenticationError",
    "BinaryResult",
    "CogniChem",
    "CogniChemError",
    "ConflictError",
    "DataResult",
    "ForbiddenError",
    "JOB_TERMINAL_STATUSES",
    "JOB_TYPES",
    "JobSubmitRequest",
    "MODEL_TYPES",
    "NotFoundError",
    "PollTimeoutError",
    "ProcessCancelledError",
    "ProcessFailedError",
    "ProcessStatus",
    "RESOURCES",
    "RateLimitError",
    "UTILITY_TYPES",
    "ValidationError",
]

__version__ = "1.0.0"
