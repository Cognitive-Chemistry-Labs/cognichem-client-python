"""Run MPNN inference against a public model."""

from __future__ import annotations

import os

from cognichem_client import CogniChem


def main() -> None:
    client = CogniChem(api_key=os.environ["COGNICHEM_API_KEY"])
    models = client.inference.models.mpnn.public()
    print("Public MPNN models:", models)

    result = client.inference.run(
        "mpnn",
        "Hydration free energy",
        {"smiles": "CCO"},
    )
    print(result.data)


if __name__ == "__main__":
    main()
