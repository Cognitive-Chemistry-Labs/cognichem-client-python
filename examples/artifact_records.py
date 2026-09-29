"""Inspect a job's result artifact and download one record instead of the zip."""

from __future__ import annotations

import os
import sys

from cognichem_client import CogniChem


def main(process_id: str) -> None:
    client = CogniChem(api_key=os.environ["COGNICHEM_API_KEY"])

    status = client.jobs.status(process_id)
    if not status.result_artifact_id:
        print("no stored artifact for", process_id, status.status)
        return

    artifact = client.artifacts.get(status.result_artifact_id)
    for port, spec in artifact.manifest.get("ports", {}).items():
        print(port, spec.get("kind"), spec.get("format"), spec.get("record_count"))

    usage = client.artifacts.usage()
    print(f"storage {usage.used_bytes}/{usage.quota_bytes} bytes")

    ports = artifact.manifest.get("ports", {})
    first = next(
        (
            (port, record["id"])
            for port, spec in ports.items()
            if port != "archive"
            for record in spec.get("records", [])
        ),
        None,
    )
    if first:
        port, record_id = first
        result = client.artifacts.download(
            artifact.id, record=record_id, port=port, save_path="."
        )
        print("saved", result.filename, len(result.content), "bytes")


if __name__ == "__main__":
    main(sys.argv[1])
