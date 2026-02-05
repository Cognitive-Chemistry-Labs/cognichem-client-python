from cognichem_client.config import ROUTE_MAP, HOSTNAME, API_V1_STR


class Client:

    def __init__(
            self,
            api_key: str,
            hostname: str = HOSTNAME,
            route_map: dict = ROUTE_MAP,
            api_v1_str: str = API_V1_STR,
         ):

        self.api_key = api_key
        self.hostname = hostname.rstrip("/")
        self.route_map = route_map
        self.api_v1_str = api_v1_str
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
