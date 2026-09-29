"""Science database lookup resource clients under ``/lookup``."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES
from cognichem_client.types import LookupResponse, PubchemLookupResponse

ChemblOperation = Literal[
    "molecule",
    "target",
    "molecule_activities",
    "target_activities",
    "similarity",
    "substructure",
]
TargetsOperation = Literal[
    "target_diseases", "disease_targets", "target_drugs", "disease_drugs"
]
EntryOrSearch = Literal["entry", "search"]
PropertyKey = Literal[
    "boiling_point",
    "melting_point",
    "density",
    "vapor_pressure",
    "vapor_density",
    "heat_of_vaporization",
    "heat_of_combustion",
    "viscosity",
    "surface_tension",
    "solubility",
    "logp",
    "henrys_law_constant",
    "flash_point",
    "autoignition_temperature",
    "refractive_index",
    "dissociation_constants",
    "other",
]


def _body(operation: str, queries: Sequence[str], **options: Any) -> dict[str, Any]:
    """Build a lookup request body, omitting unset options.

    Parameters
    ----------
    operation : str
        Lookup operation.
    queries : sequence of str
        Queries (a bare string is treated as one query).
    **options : any
        Optional fields (``limit``, ``threshold``, ``organism``, …).

    Returns
    -------
    dict
        JSON body.
    """
    items = [queries] if isinstance(queries, str) else list(queries)
    body: dict[str, Any] = {"operation": operation, "queries": items}
    body.update({k: v for k, v in options.items() if v is not None})
    return body


class LookupResource:
    """Synchronous science database lookups under ``/lookup``.

    Results carry source links and licenses; show ``attribution`` with any
    data you display. Names and ids are sent upstream; SMILES are sent only
    by ChEMBL ``similarity`` / ``substructure`` and only for API keys with
    ``allow_structure_search`` (otherwise rows come back with status
    ``structure_egress_not_allowed``).

    Parameters
    ----------
    http : HttpClient
        Shared HTTP transport.
    """

    def __init__(self, http: HttpClient) -> None:
        """Attach the shared HTTP transport.

        Parameters
        ----------
        http : HttpClient
            Shared HTTP transport.
        """
        self._http = http

    def pubchem(self, names: Sequence[str]) -> PubchemLookupResponse:
        """Resolve compound names to PubChem CIDs and SMILES.

        Parameters
        ----------
        names : sequence of str
            Up to 20 compound names (names only; structures are refused).

        Returns
        -------
        PubchemLookupResponse
            One row per name, plus attribution.
        """
        data = self._http.request(
            "POST",
            ROUTES["lookup_pubchem"],
            json={"names": [names] if isinstance(names, str) else list(names)},
        )
        return PubchemLookupResponse.model_validate(data)

    def chembl(
        self,
        operation: ChemblOperation,
        queries: Sequence[str],
        *,
        limit: int | None = None,
        threshold: int | None = None,
    ) -> LookupResponse:
        """Query ChEMBL molecules, targets, activities, or structure search.

        Parameters
        ----------
        operation : str
            ``molecule``, ``target``, ``molecule_activities``,
            ``target_activities``, ``similarity``, or ``substructure``.
        queries : sequence of str
            Up to 20 ChEMBL ids or names; SMILES for ``similarity`` /
            ``substructure``.
        limit : int or None, optional
            Rows per query (1-25, default 10).
        threshold : int or None, optional
            ``similarity`` only: percent similarity (40-100, default 70).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = self._http.request(
            "POST",
            ROUTES["lookup_chembl"],
            json=_body(operation, queries, limit=limit, threshold=threshold),
        )
        return LookupResponse.model_validate(data)

    def targets(
        self,
        operation: TargetsOperation,
        queries: Sequence[str],
        *,
        limit: int | None = None,
    ) -> LookupResponse:
        """Query Open Targets target–disease–drug associations.

        Parameters
        ----------
        operation : str
            ``target_diseases``, ``disease_targets``, ``target_drugs``, or
            ``disease_drugs``.
        queries : sequence of str
            Up to 20 target symbols, disease names, or ids.
        limit : int or None, optional
            Rows per query (1-25, default 10).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = self._http.request(
            "POST",
            ROUTES["lookup_targets"],
            json=_body(operation, queries, limit=limit),
        )
        return LookupResponse.model_validate(data)

    def uniprot(
        self,
        operation: EntryOrSearch,
        queries: Sequence[str],
        *,
        organism: str | None = None,
    ) -> LookupResponse:
        """Fetch UniProt entries or search proteins.

        Parameters
        ----------
        operation : {"entry", "search"}
            ``entry`` for accessions, ``search`` for names / genes.
        queries : sequence of str
            Up to 20 accessions or search terms.
        organism : str or None, optional
            ``search`` only: organism name or NCBI taxon id (``9606`` = human).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = self._http.request(
            "POST",
            ROUTES["lookup_uniprot"],
            json=_body(operation, queries, organism=organism),
        )
        return LookupResponse.model_validate(data)

    def pdb(
        self,
        operation: EntryOrSearch,
        queries: Sequence[str],
        *,
        limit: int | None = None,
    ) -> LookupResponse:
        """Fetch RCSB PDB entries or search structures.

        Parameters
        ----------
        operation : {"entry", "search"}
            ``entry`` for PDB ids, ``search`` for text queries.
        queries : sequence of str
            Up to 20 PDB ids or search terms.
        limit : int or None, optional
            Rows per query (1-25, default 10).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = self._http.request(
            "POST",
            ROUTES["lookup_pdb"],
            json=_body(operation, queries, limit=limit),
        )
        return LookupResponse.model_validate(data)

    def properties(
        self,
        queries: Sequence[str],
        *,
        properties: Sequence[PropertyKey] | None = None,
        limit: int | None = None,
    ) -> LookupResponse:
        """Fetch PubChem experimental properties (boiling point, density, …).

        Parameters
        ----------
        queries : sequence of str
            Up to 20 PubChem CIDs or compound names.
        properties : sequence of str or None, optional
            Property keys (e.g. ``boiling_point``, ``vapor_pressure``,
            ``logp``); defaults to a common thermophysical set.
        limit : int or None, optional
            Values per property (1-10, default 3).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = self._http.request(
            "POST",
            ROUTES["lookup_properties"],
            json=_body(
                "experimental",
                queries,
                properties=list(properties) if properties is not None else None,
                limit=limit,
            ),
        )
        return LookupResponse.model_validate(data)


class AsyncLookupResource:
    """Asynchronous science database lookups under ``/lookup``.

    Results carry source links and licenses; show ``attribution`` with any
    data you display. Names and ids are sent upstream; SMILES are sent only
    by ChEMBL ``similarity`` / ``substructure`` and only for API keys with
    ``allow_structure_search`` (otherwise rows come back with status
    ``structure_egress_not_allowed``).

    Parameters
    ----------
    http : AsyncHttpClient
        Shared async HTTP transport.
    """

    def __init__(self, http: AsyncHttpClient) -> None:
        """Attach the shared async HTTP transport.

        Parameters
        ----------
        http : AsyncHttpClient
            Shared async HTTP transport.
        """
        self._http = http

    async def pubchem(self, names: Sequence[str]) -> PubchemLookupResponse:
        """Resolve compound names to PubChem CIDs and SMILES.

        Parameters
        ----------
        names : sequence of str
            Up to 20 compound names (names only; structures are refused).

        Returns
        -------
        PubchemLookupResponse
            One row per name, plus attribution.
        """
        data = await self._http.request(
            "POST",
            ROUTES["lookup_pubchem"],
            json={"names": [names] if isinstance(names, str) else list(names)},
        )
        return PubchemLookupResponse.model_validate(data)

    async def chembl(
        self,
        operation: ChemblOperation,
        queries: Sequence[str],
        *,
        limit: int | None = None,
        threshold: int | None = None,
    ) -> LookupResponse:
        """Query ChEMBL molecules, targets, activities, or structure search.

        Parameters
        ----------
        operation : str
            ``molecule``, ``target``, ``molecule_activities``,
            ``target_activities``, ``similarity``, or ``substructure``.
        queries : sequence of str
            Up to 20 ChEMBL ids or names; SMILES for ``similarity`` /
            ``substructure``.
        limit : int or None, optional
            Rows per query (1-25, default 10).
        threshold : int or None, optional
            ``similarity`` only: percent similarity (40-100, default 70).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = await self._http.request(
            "POST",
            ROUTES["lookup_chembl"],
            json=_body(operation, queries, limit=limit, threshold=threshold),
        )
        return LookupResponse.model_validate(data)

    async def targets(
        self,
        operation: TargetsOperation,
        queries: Sequence[str],
        *,
        limit: int | None = None,
    ) -> LookupResponse:
        """Query Open Targets target–disease–drug associations.

        Parameters
        ----------
        operation : str
            ``target_diseases``, ``disease_targets``, ``target_drugs``, or
            ``disease_drugs``.
        queries : sequence of str
            Up to 20 target symbols, disease names, or ids.
        limit : int or None, optional
            Rows per query (1-25, default 10).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = await self._http.request(
            "POST",
            ROUTES["lookup_targets"],
            json=_body(operation, queries, limit=limit),
        )
        return LookupResponse.model_validate(data)

    async def uniprot(
        self,
        operation: EntryOrSearch,
        queries: Sequence[str],
        *,
        organism: str | None = None,
    ) -> LookupResponse:
        """Fetch UniProt entries or search proteins.

        Parameters
        ----------
        operation : {"entry", "search"}
            ``entry`` for accessions, ``search`` for names / genes.
        queries : sequence of str
            Up to 20 accessions or search terms.
        organism : str or None, optional
            ``search`` only: organism name or NCBI taxon id (``9606`` = human).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = await self._http.request(
            "POST",
            ROUTES["lookup_uniprot"],
            json=_body(operation, queries, organism=organism),
        )
        return LookupResponse.model_validate(data)

    async def pdb(
        self,
        operation: EntryOrSearch,
        queries: Sequence[str],
        *,
        limit: int | None = None,
    ) -> LookupResponse:
        """Fetch RCSB PDB entries or search structures.

        Parameters
        ----------
        operation : {"entry", "search"}
            ``entry`` for PDB ids, ``search`` for text queries.
        queries : sequence of str
            Up to 20 PDB ids or search terms.
        limit : int or None, optional
            Rows per query (1-25, default 10).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = await self._http.request(
            "POST",
            ROUTES["lookup_pdb"],
            json=_body(operation, queries, limit=limit),
        )
        return LookupResponse.model_validate(data)

    async def properties(
        self,
        queries: Sequence[str],
        *,
        properties: Sequence[PropertyKey] | None = None,
        limit: int | None = None,
    ) -> LookupResponse:
        """Fetch PubChem experimental properties (boiling point, density, …).

        Parameters
        ----------
        queries : sequence of str
            Up to 20 PubChem CIDs or compound names.
        properties : sequence of str or None, optional
            Property keys (e.g. ``boiling_point``, ``vapor_pressure``,
            ``logp``); defaults to a common thermophysical set.
        limit : int or None, optional
            Values per property (1-10, default 3).

        Returns
        -------
        LookupResponse
            Results in input order, plus attribution.
        """
        data = await self._http.request(
            "POST",
            ROUTES["lookup_properties"],
            json=_body(
                "experimental",
                queries,
                properties=list(properties) if properties is not None else None,
                limit=limit,
            ),
        )
        return LookupResponse.model_validate(data)
