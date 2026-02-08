from cognichem_client.config import ROUTE_MAP, HOSTNAME, API_V1_STR


class Client:
    """Base client class for interacting with the CogniChem API."""

    def __init__(
            self,
            api_key: str,
            hostname: str = HOSTNAME,
            route_map: dict = ROUTE_MAP,
            api_v1_str: str = API_V1_STR,
         ):
        """
        Initializes the Client with the provided API key and configuration.

        Parameters
        ----------
        api_key : str
            The API key for authenticating with the CogniChem API.
        hostname : str, optional
            The base URL of the CogniChem API (default is HOSTNAME).
        route_map : dict, optional
            A dictionary mapping endpoint names to their URL paths (default is
            ROUTE_MAP).
        api_v1_str : str, optional
            The API version string to use in endpoint URLs (default is
            API_V1_STR).
        """

        self.api_key = api_key
        self.hostname = hostname.rstrip("/")
        self.route_map = route_map
        self.api_v1_str = api_v1_str
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
