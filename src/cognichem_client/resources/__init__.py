"""API resource modules for sync CogniChem clients.

Exposes resource classes used by :class:`~cognichem_client.client.CogniChem`
(auth, API keys, jobs, inference, utilities, usage limits, workflows,
artifacts, events, wallet, lookups, reference KG, and Assistant chat). Async
counterparts live alongside these modules and are wired by
:class:`~cognichem_client.async_client.AsyncCogniChem`.
"""

from cognichem_client.resources.api_keys import ApiKeysResource
from cognichem_client.resources.artifacts import ArtifactsResource
from cognichem_client.resources.auth import AuthResource
from cognichem_client.resources.chat import ChatResource
from cognichem_client.resources.events import EventsResource
from cognichem_client.resources.inference import InferenceResource
from cognichem_client.resources.jobs import JobsResource
from cognichem_client.resources.lookup import LookupResource
from cognichem_client.resources.reference import ReferenceResource
from cognichem_client.resources.usage import UsageResource
from cognichem_client.resources.utils import UtilsResource
from cognichem_client.resources.wallet import WalletResource
from cognichem_client.resources.workflows import WorkflowsResource

__all__ = [
    "ApiKeysResource",
    "ArtifactsResource",
    "AuthResource",
    "ChatResource",
    "EventsResource",
    "InferenceResource",
    "JobsResource",
    "LookupResource",
    "ReferenceResource",
    "UsageResource",
    "UtilsResource",
    "WalletResource",
    "WorkflowsResource",
]
