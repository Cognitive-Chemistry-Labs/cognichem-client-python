import requests
import time
from typing import Dict, Any

from cognichem_client.clients import Client
from cognichem_client.exceptions import CogniChemAPIError


class InferenceClient(Client):
    """
    Client for interacting with the inference endpoints of the CogniChem API.
    """

    def run(self, model_type: str, model_name: str, payload: dict) -> Dict[str, Any]:
        """
        Runs an inference job and waits for it to complete, returning the result.

        Parameters
        ----------
        model_type : str
            The type of model to run (e.g. "mpnn").
        model_name : str
            The name of the model to run.
        payload : dict
            The input payload for the inference job.

        Returns
        -------
        Dict[str, Any]
            The result of the inference job.
        """

        process_id = self.submit(model_type, model_name, payload)
        status = ""
        message = ""
        while status != "completed" and status != "error":
            time.sleep(0.3)
            resp = self.status(process_id)
            status = resp.get("status", "")
            message = resp.get("message", "")
        if status == "completed":
            return self.result(process_id)
        else:
            raise CogniChemAPIError(
                f"Inference job {process_id} failed: {message}"
            )
        
    def get_models(self, public=False) -> Dict[str, Any]:
        """
        Gets a list of available models for inference.

        Parameters
        ----------
        public : bool, optional
            Whether to return only public models (default is False, which
            returns user models).

        Returns
        -------
        Dict[str, Any]
            A list of available models for inference.
        """

        if public:
            url = f"{self.hostname}{self.route_map['public_models_mpnn']}"
        else:
            url = f"{self.hostname}{self.route_map['user_models_mpnn']}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def get_model(self, model_name: str) -> Dict[str, Any]:
        """
        Gets details of a specific model.

        Parameters
        ----------
        model_name : str
            The name of the model to retrieve.

        Returns
        -------
        Dict[str, Any]
            Details of the specified model.
        """

        url = f"{self.hostname}{self.route_map['user_models_mpnn']}"
        resp = requests.get(url, params={
            "model_name": model_name,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()

    def submit(
            self,
            model_type: str,
            model_name: str,
            payload: dict
         ) -> str:
        """
        Submits an inference job to the API.

        Parameters
        ----------
        model_type : str
            The type of model to run (e.g. "mpnn").
        model_name : str
            The name of the model to run.
        payload : dict
            The input payload for the inference job.

        Returns
        -------
        str
            The process ID of the submitted inference job.
        """

        url = f"{self.hostname}{self.route_map['inference_submit']}"
        resp = requests.post(url, json={
            "model_type": model_type,
            "model_name": model_name,
            "payload": payload
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()["process_id"]
    
    def status(self, process_id: str) -> Dict[str, Any]:
        """
        Gets the status of an inference job.

        Parameters
        ----------
        process_id : str
            The process ID of the inference job.

        Returns
        -------
        Dict[str, Any]
            The status of the inference job.
        """

        url = f"{self.hostname}{self.route_map['inference_status']}"
        resp = requests.get(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def result(self, process_id: str) -> Dict[str, Any]:
        """
        Gets the result of an inference job.

        Parameters
        ----------
        process_id : str
            The process ID of the inference job.

        Returns
        -------
        Dict[str, Any]
            The result of the inference job.
        """

        url = f"{self.hostname}{self.route_map['inference_result']}"
        resp = requests.get(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def list(self) -> Dict[str, Any]:
        """
        Lists all inference jobs.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing all inference jobs.
        """

        url = f"{self.hostname}{self.route_map['inference_list']}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def delete(self, process_id: str) -> Dict[str, Any]:
        """
        Deletes an inference job, which can be used to cancel a running job or
        remove a completed job from the list.

        Parameters
        ----------
        process_id : str
            The process ID of the inference job.

        Returns
        -------
        Dict[str, Any]
            The response from the API after deleting the inference job.
        """

        url = f"{self.hostname}{self.route_map['inference_delete']}"
        resp = requests.delete(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
