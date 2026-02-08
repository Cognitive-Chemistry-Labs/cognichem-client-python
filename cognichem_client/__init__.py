from cognichem_client.clients.inference import InferenceClient
from cognichem_client.clients.jobs import JobsClient
from cognichem_client.clients.utility import UtilityClient

from .config import HOSTNAME, API_V1_STR, ROUTE_MAP


class CogniChemClient:
    """
    Main client class for interacting with the CogniChem API.
    Initializes sub-clients for inference, jobs, and utility endpoints.
    """

    def __init__(self, api_key: str):
        """
        Initializes the CogniChemClient with the provided API key and sets up
        sub-clients.

        Parameters
        ----------
        api_key : str
            The API key for authenticating with the CogniChem API.
        """

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
