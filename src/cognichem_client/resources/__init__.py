"""API resource modules for sync CogniChem clients.

Exposes resource classes used by :class:`~cognichem_client.client.CogniChem`
(auth, API keys, jobs, inference, utilities, and usage limits). Async
counterparts live alongside these modules and are wired by
:class:`~cognichem_client.async_client.AsyncCogniChem`.
"""

from cognichem_client.resources.api_keys import ApiKeysResource
from cognichem_client.resources.auth import AuthResource
from cognichem_client.resources.inference import InferenceResource
from cognichem_client.resources.jobs import JobsResource
from cognichem_client.resources.usage import UsageResource
from cognichem_client.resources.utils import UtilsResource

__all__ = [
    "ApiKeysResource",
    "AuthResource",
    "InferenceResource",
    "JobsResource",
    "UsageResource",
    "UtilsResource",
]
