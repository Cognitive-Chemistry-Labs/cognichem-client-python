import requests
import time
from typing import Dict, Any

from cognichem_client.clients import Client
from cognichem_client.exceptions import CogniChemAPIError


class InferenceClient(Client):

    def run(self, model_type: str, model_name: str, payload: dict) -> Dict[str, Any]:

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

        if public:
            url = f"{self.hostname}{self.route_map['public_models_mpnn']}"
        else:
            url = f"{self.hostname}{self.route_map['user_models_mpnn']}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def get_model(self, model_name: str) -> Dict[str, Any]:

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

        url = f"{self.hostname}{self.route_map['inference_status']}"
        resp = requests.get(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def result(self, process_id: str) -> Dict[str, Any]:

        url = f"{self.hostname}{self.route_map['inference_result']}"
        resp = requests.get(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def list(self) -> Dict[str, Any]:

        url = f"{self.hostname}{self.route_map['inference_list']}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def delete(self, process_id: str) -> Dict[str, Any]:

        url = f"{self.hostname}{self.route_map['inference_delete']}"
        resp = requests.delete(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
