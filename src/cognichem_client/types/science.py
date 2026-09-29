"""Models for science lookups (``/lookup/*``) and the reference KG (``/reference``)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LookupItem(BaseModel):
    """One lookup result.

    Attributes
    ----------
    source : str
        Upstream source (``ChEMBL``, ``Open Targets``, ``UniProt``, ``RCSB PDB``,
        ``PubChem``).
    operation : str
        Operation that produced the row.
    query : str or None
        Input query the row answers.
    status : str
        ``found``, ``ambiguous``, ``not_found``, ``error``, or
        ``structure_egress_not_allowed``.
    record_id : str or None
        Source record id.
    title : str or None
        Record title.
    url : str or None
        Public source link (cite it).
    release : str or None
        Source release, when known.
    license : str
        Data license.
    data : any
        Source-specific payload.
    """

    source: str
    operation: str
    query: str | None = None
    status: str
    record_id: str | None = None
    title: str | None = None
    url: str | None = None
    release: str | None = None
    license: str = ""
    data: Any = None


class LookupResponse(BaseModel):
    """Lookup results in input order plus source attribution.

    Attributes
    ----------
    results : list of LookupItem
        One or more rows per query.
    attribution : str
        Attribution text to show with the data.
    """

    results: list[LookupItem] = Field(default_factory=list)
    attribution: str = ""


class PubchemCompound(BaseModel):
    """One PubChem name resolution.

    Attributes
    ----------
    name : str
        Queried compound name.
    status : str
        ``found``, ``ambiguous``, ``not_found``, or ``error``.
    cid : int or None
        PubChem CID.
    title : str or None
        PubChem title.
    smiles : str or None
        Resolved SMILES.
    url : str or None
        PubChem compound page.
    other_cids : list of int or None
        Other candidate CIDs when ambiguous.
    source : str
        Always ``PubChem``.
    license : str
        Data license.
    """

    name: str
    status: str
    cid: int | None = None
    title: str | None = None
    smiles: str | None = None
    url: str | None = None
    other_cids: list[int] | None = None
    source: str = "PubChem"
    license: str = ""


class PubchemLookupResponse(BaseModel):
    """Resolved compounds in input order plus source attribution.

    Attributes
    ----------
    compounds : list of PubchemCompound
        One row per name.
    attribution : str
        Attribution text to show with the data.
    """

    compounds: list[PubchemCompound] = Field(default_factory=list)
    attribution: str = ""


class ReferencePaper(BaseModel):
    """One paper in the reference KG (public metadata and links).

    Attributes
    ----------
    id : str
        Paper id (``paper:…``).
    title : str
        Title.
    year : int or None
        Publication year.
    venue : str or None
        Journal or venue.
    authors : list of str
        First authors (capped).
    authors_total : int
        Total author count.
    doi : str or None
        DOI.
    url : str or None
        Public landing link.
    oa_url : str or None
        Open-access link, when known.
    paper_set : str
        ``method``, ``used_cognichem``, or ``general``.
    abstract : str or None
        Abstract (only on get, and only when licensed CC0 / CC BY).
    abstract_license : str or None
        ``CC0`` or ``CC BY`` when an abstract is stored.
    abstract_license_url : str or None
        Creative Commons page for ``abstract_license``.
    abstract_source : str or None
        ``Europe PMC`` when an abstract is stored.
    abstract_notice : str or None
        How the stored abstract differs from the original.
    source : str
        Ingest source.
    retrieved_at : str or None
        ISO-8601 retrieval time.
    """

    id: str
    title: str
    year: int | None = None
    venue: str | None = None
    authors: list[str] = Field(default_factory=list)
    authors_total: int = 0
    doi: str | None = None
    url: str | None = None
    oa_url: str | None = None
    paper_set: str
    abstract: str | None = None
    abstract_license: str | None = None
    abstract_license_url: str | None = None
    abstract_source: str | None = None
    abstract_notice: str | None = None
    source: str = ""
    retrieved_at: str | None = None


class ReferenceEdge(BaseModel):
    """A paper → paper or paper → Product KG node link.

    Attributes
    ----------
    src_paper_id : str
        Source paper id.
    dst_kind : str
        ``paper`` or ``product_node``.
    dst_id : str
        Destination id (e.g. ``job_type:protein-prepare``).
    kind : str
        ``cites``, ``method_of``, ``uses_tool``, ``compares``, or
        ``describes``.
    """

    src_paper_id: str
    dst_kind: str
    dst_id: str
    kind: str


class ReferenceProvenance(BaseModel):
    """Where a reference answer came from.

    Attributes
    ----------
    source : str
        Always ``cognichem_reference_kg``.
    entity_ids : list of str
        Entity ids used in the answer.
    outbound : list of dict
        Public links to cite.
    """

    source: str = "cognichem_reference_kg"
    entity_ids: list[str] = Field(default_factory=list)
    outbound: list[dict[str, str]] = Field(default_factory=list)


class ReferenceSearchResponse(BaseModel):
    """Ranked paper hits from ``GET /reference/papers``.

    Attributes
    ----------
    query : str
        Search text.
    mode : str
        ``hybrid`` when the query embedding was used, else ``lexical``.
    papers : list of ReferencePaper
        Ranked hits.
    provenance : ReferenceProvenance
        Answer provenance.
    """

    query: str
    mode: str = "lexical"
    papers: list[ReferencePaper] = Field(default_factory=list)
    provenance: ReferenceProvenance = Field(default_factory=ReferenceProvenance)


class ReferencePaperDetail(BaseModel):
    """One paper plus its links, from ``GET /reference/papers/{paper_id}``.

    Attributes
    ----------
    paper : ReferencePaper
        The paper.
    edges : list of ReferenceEdge
        Outgoing links.
    cited_by_count : int
        Reference-KG papers that cite this one.
    provenance : ReferenceProvenance
        Answer provenance.
    """

    paper: ReferencePaper
    edges: list[ReferenceEdge] = Field(default_factory=list)
    cited_by_count: int = 0
    provenance: ReferenceProvenance = Field(default_factory=ReferenceProvenance)


class ReferenceNeighborhood(BaseModel):
    """Papers linked to a Product KG node or a paper.

    Attributes
    ----------
    center : str
        Node or paper id the neighborhood is centered on.
    edges : list of ReferenceEdge
        Links around the center.
    papers : list of ReferencePaper
        Linked papers.
    provenance : ReferenceProvenance
        Answer provenance.
    """

    center: str
    edges: list[ReferenceEdge] = Field(default_factory=list)
    papers: list[ReferencePaper] = Field(default_factory=list)
    provenance: ReferenceProvenance = Field(default_factory=ReferenceProvenance)
