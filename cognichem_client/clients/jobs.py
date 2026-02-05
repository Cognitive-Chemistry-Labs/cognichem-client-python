import requests
import time
from typing import Any, Dict

from cognichem_client.clients import Client
from cognichem_client.exceptions import CogniChemAPIError


class JobsClient(Client):

    def run(self, job_name: str, job_type: str, payload: dict, get_result: bool = True) -> Dict[str, Any]:

        process_id = self.submit(job_name, job_type, payload)
        status = ""
        message = ""
        while status != "completed" and status != "error":
            time.sleep(30)
            resp = self.status(process_id)
            status = resp.get("status", "")
            message = resp.get("message", "")
        if status == "completed":
            if get_result:
                return self.result(process_id)
            else:
                return {"process_id": process_id}
        else:
            raise CogniChemAPIError(
                f"Job {process_id} failed: {message}"
            )

    def submit(self, job_name: str, job_type: str, payload: dict) -> str:

        url = f"{self.hostname}{self.route_map['job_submit']}"
        resp = requests.post(url, json={
            "job_name": job_name,
            "job_type": job_type,
            "payload": payload,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()["process_id"]
    
    def status(self, process_id: str) -> Dict[str, Any]:

        url = f"{self.hostname}{self.route_map['job_status']}"
        resp = requests.get(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def result(self, process_id: str) -> Dict[str, Any]:

        url = f"{self.hostname}{self.route_map['job_result']}"
        resp = requests.get(url, params={
            "process_id": process_id,
        }, headers=self.headers, stream=True)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        content_disposition = resp.headers.get("Content-Disposition", "")
        filename = None
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[-1].strip('"')
        media_type = resp.headers.get("Content-Type", None)
        content = resp.content
        return {
            "filename": filename,
            "media_type": media_type,
            "content": content,
        }
    
    def list(self) -> Dict[str, Any]:

        url = f"{self.hostname}{self.route_map['job_list']}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def cancel(self, process_id: str) -> Dict[str, Any]:

        url = f"{self.hostname}{self.route_map['job_cancel']}"
        resp = requests.delete(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def delete(self, process_id: str) -> Dict[str, Any]:

        url = f"{self.hostname}{self.route_map['job_delete']}"
        resp = requests.delete(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
