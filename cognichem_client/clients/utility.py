import requests
import time
from typing import Any, Dict

from cognichem_client.clients import Client
from cognichem_client.exceptions import CogniChemAPIError


class UtilityClient(Client):
    """
    Client for interacting with the utility endpoints of the CogniChem API.
    """

    def run(self, utility_type: str, payload: dict) -> Dict[str, Any]:
        """
        Runs a utility job and waits for it to complete, returning the result.

        Parameters
        ----------
        utility_type : str
            The type of utility to run (e.g. "convert").
        payload : dict
            The input payload for the utility job.

        Returns
        -------
        Dict[str, Any]
            The result of the utility job.
        """

        process_id = self.submit(utility_type, payload)
        status = ""
        message = ""
        while status != "completed" and status != "error":
            time.sleep(0.3)
            status_resp = self.status(process_id)
            status = status_resp.get("status", "")
            message = status_resp.get("message", "")
        if status == "completed":
            return self.result(process_id)
        else:
            raise CogniChemAPIError(
                f"Utility job {process_id} failed: {message}"
            )

    def submit(
            self,
            utility_type: str,
            payload: dict
         ) -> str:
        """
        Submits a utility job to the CogniChem API.

        Parameters
        ----------
        utility_type : str
            The type of utility to run (e.g. "convert").
        payload : dict
            The input payload for the utility job.

        Returns
        -------
        str
            The process ID of the submitted utility job.
        """

        url = f"{self.hostname}{self.route_map['utils_submit']}"
        resp = requests.post(url, json={
            "utility_type": utility_type,
            "payload": payload
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()["process_id"]
    
    def status(self, process_id: str) -> Dict[str, Any]:
        """
        Gets the status of a utility job.

        Parameters
        ----------
        process_id : str
            The process ID of the utility job.

        Returns
        -------
        Dict[str, Any]
            The status of the utility job.
        """

        url = f"{self.hostname}{self.route_map['utils_status']}"
        resp = requests.get(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def result(self, process_id: str) -> Dict[str, Any]:
        """
        Gets the result of a utility job.

        Parameters
        ----------
        process_id : str
            The process ID of the utility job.

        Returns
        -------
        Dict[str, Any]
            The result of the utility job.
        """

        url = f"{self.hostname}{self.route_map['utils_result']}"
        resp = requests.get(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def list(self) -> Dict[str, Any]:
        """
        Lists all running/completed utility jobs.

        Returns
        -------
        Dict[str, Any]
            A list of all running/completed utility jobs.
        """

        url = f"{self.hostname}{self.route_map['utils_list']}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def delete(self, process_id: str) -> Dict[str, Any]:
        """
        Deletes a utility job, which can be used to cancel a running job or
        remove a completed job from the list.

        Parameters
        ----------
        process_id : str
            The process ID of the utility job.

        Returns
        -------
        Dict[str, Any]
            The response from the delete operation.
        """

        url = f"{self.hostname}{self.route_map['utils_delete']}"
        resp = requests.delete(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
