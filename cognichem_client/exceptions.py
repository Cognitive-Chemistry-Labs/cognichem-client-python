class CogniChemAPIError(Exception):
    """
    Custom exception for handling API errors from the CogniChem API.
    """
    
    def __init__(self, response):

        self.status_code = response.status_code
        try:
            self.detail = response.json().get("default", response.text)
        except Exception:
            self.detail = response.text
        super().__init__(f"API Error {self.status_code}: {self.detail}")
