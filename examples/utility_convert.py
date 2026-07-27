"""Convert a SMILES string to a PDB block via the utils API."""

from __future__ import annotations

import os

from cognichem_client import CogniChem


def main() -> None:
    client = CogniChem(api_key=os.environ["COGNICHEM_API_KEY"])
    result = client.utils.run(
        "convert",
        {
            "input_data": "CCO",
            "input_format": "smiles",
            "output_format": "pdbblock",
        },
    )
    print(result.data)


if __name__ == "__main__":
    main()
