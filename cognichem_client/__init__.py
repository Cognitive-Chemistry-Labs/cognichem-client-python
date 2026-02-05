from cognichem_client.clients.inference import InferenceClient
from cognichem_client.clients.jobs import JobsClient
from cognichem_client.clients.utility import UtilityClient

from .config import HOSTNAME, API_V1_STR, ROUTE_MAP


class CogniChemClient:

    def __init__(self, api_key: str):

        self.inference = InferenceClient(
            api_key=api_key,
            hostname=HOSTNAME,
            route_map=ROUTE_MAP,
            api_v1_str=API_V1_STR,
        )
        self.jobs = JobsClient(
            api_key=api_key,
            hostname=HOSTNAME,
            route_map=ROUTE_MAP,
            api_v1_str=API_V1_STR,
        )
        self.utility = UtilityClient(
            api_key=api_key,
            hostname=HOSTNAME,
            route_map=ROUTE_MAP,
            api_v1_str=API_V1_STR,
        )
