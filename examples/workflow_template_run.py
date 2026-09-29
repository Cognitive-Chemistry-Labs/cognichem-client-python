"""Run a curated workflow template: upload a target, validate, estimate, run."""

from __future__ import annotations

import os
import sys
import uuid

from cognichem_client import CogniChem, artifact_ref


def main(pdb_path: str) -> None:
    client = CogniChem(api_key=os.environ["COGNICHEM_API_KEY"])

    for template in client.workflows.templates():
        print(f"{template.id:32} {template.complexity:9} {template.summary}")
    spec = client.workflows.template("smiles-embed-dock").spec

    # Structure params take an $artifact ref, so upload the PDB first.
    target = client.artifacts.upload(
        pdb_path, data_kind="protein_structure", data_format="pdb"
    )
    port = next(iter(target.manifest.get("ports", {})), "structure")
    params = {
        "ligands": ["CCO", "c1ccccc1O"],
        "target_structure": artifact_ref(target.id, port),
    }

    check = client.workflows.validate(spec, params=params)
    if not check.valid:
        for error in check.errors:
            print("invalid:", error.code, error.message)
        return
    estimate = client.workflows.estimate(spec, params=params)
    print(f"estimated hold ${estimate.total:.4f} at tier {estimate.tier}")

    run = client.workflows.runs.run(
        f"example-dock-{uuid.uuid4().hex[:8]}",
        spec,
        params=params,
        max_run_cost=estimate.total * 1.5,
    )
    print("run", run.id, run.status, f"charged ${run.charged_amount:.4f}")
    for item in client.workflows.runs.artifacts(run.id).items:
        print(" ", item.step_key, item.port, item.artifact_id, item.record_count)


if __name__ == "__main__":
    main(sys.argv[1])
