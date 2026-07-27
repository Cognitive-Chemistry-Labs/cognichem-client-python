"""Submit a short job, wait for completion, and download the result artifact."""

from __future__ import annotations

import os
import uuid

from cognichem_client import CogniChem


def main() -> None:
    client = CogniChem(api_key=os.environ["COGNICHEM_API_KEY"])
    job_name = f"example-padel-{uuid.uuid4().hex[:8]}"

    submitted = client.jobs.submit(
        job_name=job_name,
        job_type="padel-descriptor",
        payload={
            "input_data": ["CCO", "CCC"],
            "input_format": "smiles",
            "descriptor_types": ["ALOGP", "AtomCount", "HBondAcceptorCount"],
        },
        idempotency_key=str(uuid.uuid4()),
    )
    print("submitted", submitted.process_id)

    status = client.jobs.wait(submitted.process_id, poll_interval=5.0, timeout=1800)
    print("status", status.status, status.message)

    if status.status == "completed":
        artifact = client.jobs.result(submitted.process_id, save_path=".")
        print("saved", artifact.filename, "bytes=", len(artifact.content))


if __name__ == "__main__":
    main()
