import requests
import time
from typing import Any, Dict

from cognichem_client.clients import Client
from cognichem_client.exceptions import CogniChemAPIError


class JobsClient(Client):
    """
    Client for interacting with the job endpoints of the CogniChem API.
    """

    def run(
            self,
            job_name: str,
            job_type: str,
            payload: dict,
            get_result: bool = True,
            save: bool = False,
            save_dir: str = "./",
         ) -> Dict[str, Any]:
        """
        Runs a job and waits for it to complete, returning the result.

        Parameters
        ----------
        job_name : str
            The name of the job to run.
        job_type : str
            The type of job to run (e.g. "inference", "utility").
        payload : dict
            The input payload for the job.
        get_result : bool, optional
            Whether to return the job result after completion (default is
            True).
        save : bool, optional
            Whether to save the job result to a file if the result is a file
            (default is False).
        save_dir : str, optional
            The directory to save the job result file if save is True (default
            is "./").

        Returns
        -------
        Dict[str, Any]
            The result of the job, which may include the filename, media type,
            and content if the result is a file.
        """

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
                return self.result(process_id, save=save, save_dir=save_dir)
            else:
                return {"process_id": process_id}
        else:
            raise CogniChemAPIError(
                f"Job {process_id} failed: {message}"
            )

    def submit(self, job_name: str, job_type: str, payload: dict) -> str:
        """
        Submits a job to the CogniChem API.

        Parameters
        ----------
        job_name : str
            The name of the job to submit.
        job_type : str
            The type of job to submit (e.g. "inference", "utility").
        payload : dict
            The input payload for the job.

        Returns
        -------
        str
            The process ID of the submitted job.
        """

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
        """
        Retrieves the status of a job.

        Parameters
        ----------
        process_id : str
            The ID of the process to retrieve the status for.

        Returns
        -------
        Dict[str, Any]
            The status of the job.
        """

        url = f"{self.hostname}{self.route_map['job_status']}"
        resp = requests.get(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def result(self, process_id: str, save=False, save_dir="./") -> Dict[str, Any]:
        """
        Retrieves the result of a job.

        Parameters
        ----------
        process_id : str
            The ID of the process to retrieve the result for.
        save : bool, optional
            Whether to save the job result to a file if the result is a file
            (default is False).
        save_dir : str, optional
            The directory to save the job result file if save is True (default
            is "./").

        Returns
        -------
        Dict[str, Any]
            The result of the job, which may include the filename, media type,
            and content if the result is a file.
        """

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
        if save and filename:
            with open(f"{save_dir}/{filename}", "wb") as f:
                f.write(content)
        return {
            "filename": filename,
            "media_type": media_type,
            "content": content,
        }
    
    def list(self) -> Dict[str, Any]:
        """
        Lists all running/completed jobs.

        Returns
        -------
        Dict[str, Any]
            A list of all running/completed jobs.
        """

        url = f"{self.hostname}{self.route_map['job_list']}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def cancel(self, process_id: str) -> Dict[str, Any]:
        """
        Cancels a running job.

        Parameters
        ----------
        process_id : str
            The ID of the process to cancel.

        Returns
        -------
        Dict[str, Any]
            The response from the API after attempting to cancel the job.
        """

        url = f"{self.hostname}{self.route_map['job_cancel']}"
        resp = requests.delete(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
    
    def delete(self, process_id: str) -> Dict[str, Any]:
        """
        Deletes a job.

        Parameters
        ----------
        process_id : str
            The ID of the process to delete.

        Returns
        -------
        Dict[str, Any]
            The response from the API after attempting to delete the job.
        """

        url = f"{self.hostname}{self.route_map['job_delete']}"
        resp = requests.delete(url, params={
            "process_id": process_id,
        }, headers=self.headers)
        if resp.status_code != 200:
            raise CogniChemAPIError(resp)
        return resp.json()
