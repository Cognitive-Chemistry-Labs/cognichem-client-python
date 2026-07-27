"""Submit multiple jobs in one request."""

from __future__ import annotations

import os
import uuid

from cognichem_client import CogniChem, JobSubmitRequest


def main() -> None:
    client = CogniChem(api_key=os.environ["COGNICHEM_API_KEY"])
    suffix = uuid.uuid4().hex[:8]
    response = client.jobs.submit_many(
        [
            JobSubmitRequest(
                job_name=f"batch-padel-{suffix}-a",
                job_type="padel-descriptor",
                payload={
                    "input_data": ["CCO"],
                    "input_format": "smiles",
                    "descriptor_types": ["ALOGP"],
                },
            ),
            JobSubmitRequest(
                job_name=f"batch-padel-{suffix}-b",
                job_type="padel-descriptor",
                payload={
                    "input_data": ["CCC"],
                    "input_format": "smiles",
                    "descriptor_types": ["AtomCount"],
                },
            ),
        ],
        idempotency_key=str(uuid.uuid4()),
    )
    print("process_ids", response.process_ids)


if __name__ == "__main__":
    main()
