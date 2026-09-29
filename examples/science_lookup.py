"""Resolve a compound, look up target activities, and find method papers."""

from __future__ import annotations

import os

from cognichem_client import CogniChem


def main() -> None:
    client = CogniChem(api_key=os.environ["COGNICHEM_API_KEY"])

    compounds = client.lookup.pubchem(["aspirin"])
    for compound in compounds.compounds:
        print(compound.name, compound.status, compound.cid, compound.smiles)

    activities = client.lookup.chembl("target_activities", ["EGFR"], limit=5)
    for row in activities.results:
        print(row.status, row.record_id, row.title, row.url)
    print(activities.attribution)

    papers = client.reference.search("protonation state pKa", paper_set="method")
    for paper in papers.papers:
        print(paper.year, paper.title, paper.url)

    print("wallet", client.wallet.balance())


if __name__ == "__main__":
    main()
