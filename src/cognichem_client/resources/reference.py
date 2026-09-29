"""Reference-KG (literature) resource clients under ``/reference``."""

from __future__ import annotations

from typing import Any

from cognichem_client._http import AsyncHttpClient, HttpClient
from cognichem_client.constants import ROUTES, ReferenceEdgeKind, ReferencePaperSet
from cognichem_client.types import (
    ReferenceNeighborhood,
    ReferencePaperDetail,
    ReferenceSearchResponse,
)


class ReferenceResource:
    """Synchronous reference-KG (literature) endpoints under ``/reference``.

    The reference KG holds method papers for every catalog job type, papers
    that use CogniChem tools, and curated general papers.

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

    def search(
        self,
        q: str,
        *,
        paper_set: ReferencePaperSet | None = None,
        limit: int = 10,
    ) -> ReferenceSearchResponse:
        """Search reference papers (hybrid semantic + lexical when available).

        Parameters
        ----------
        q : str
            Search text (1-200 characters).
        paper_set : {"method", "used_cognichem", "general"} or None, optional
            Keep only one paper set.
        limit : int, optional
            Hits to return (1-50).

        Returns
        -------
        ReferenceSearchResponse
            Ranked papers and provenance.
        """
        params: dict[str, Any] = {"q": q, "limit": limit}
        if paper_set is not None:
            params["paper_set"] = paper_set
        data = self._http.request("GET", ROUTES["reference_papers"], params=params)
        return ReferenceSearchResponse.model_validate(data)

    def get(self, paper_id: str) -> ReferencePaperDetail:
        """Fetch one paper with its links (and abstract, when licensed).

        Parameters
        ----------
        paper_id : str
            Paper id (``paper:…``).

        Returns
        -------
        ReferencePaperDetail
            Paper, edges, citing count, and provenance.
        """
        data = self._http.request(
            "GET", ROUTES["reference_paper"].format(paper_id=paper_id)
        )
        return ReferencePaperDetail.model_validate(data)

    def neighborhood(
        self,
        *,
        node_id: str | None = None,
        paper_id: str | None = None,
        kind: ReferenceEdgeKind | None = None,
        limit: int = 25,
    ) -> ReferenceNeighborhood:
        """Return papers linked to a Product KG node or to a paper.

        Parameters
        ----------
        node_id : str or None, optional
            Product KG node (e.g. ``job_type:protein-prepare``).
        paper_id : str or None, optional
            Paper id. Give ``node_id`` or ``paper_id``.
        kind : str or None, optional
            Keep only one edge kind (``cites``, ``method_of``, ``uses_tool``,
            ``compares``, ``describes``).
        limit : int, optional
            Edges to return (1-50).

        Returns
        -------
        ReferenceNeighborhood
            Center, edges, papers, and provenance.
        """
        params: dict[str, Any] = {"limit": limit}
        for key, value in (
            ("node_id", node_id),
            ("paper_id", paper_id),
            ("kind", kind),
        ):
            if value is not None:
                params[key] = value
        data = self._http.request(
            "GET", ROUTES["reference_neighborhood"], params=params
        )
        return ReferenceNeighborhood.model_validate(data)


class AsyncReferenceResource:
    """Asynchronous reference-KG (literature) endpoints under ``/reference``.

    The reference KG holds method papers for every catalog job type, papers
    that use CogniChem tools, and curated general papers.

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

    async def search(
        self,
        q: str,
        *,
        paper_set: ReferencePaperSet | None = None,
        limit: int = 10,
    ) -> ReferenceSearchResponse:
        """Search reference papers (hybrid semantic + lexical when available).

        Parameters
        ----------
        q : str
            Search text (1-200 characters).
        paper_set : {"method", "used_cognichem", "general"} or None, optional
            Keep only one paper set.
        limit : int, optional
            Hits to return (1-50).

        Returns
        -------
        ReferenceSearchResponse
            Ranked papers and provenance.
        """
        params: dict[str, Any] = {"q": q, "limit": limit}
        if paper_set is not None:
            params["paper_set"] = paper_set
        data = await self._http.request(
            "GET", ROUTES["reference_papers"], params=params
        )
        return ReferenceSearchResponse.model_validate(data)

    async def get(self, paper_id: str) -> ReferencePaperDetail:
        """Fetch one paper with its links (and abstract, when licensed).

        Parameters
        ----------
        paper_id : str
            Paper id (``paper:…``).

        Returns
        -------
        ReferencePaperDetail
            Paper, edges, citing count, and provenance.
        """
        data = await self._http.request(
            "GET", ROUTES["reference_paper"].format(paper_id=paper_id)
        )
        return ReferencePaperDetail.model_validate(data)

    async def neighborhood(
        self,
        *,
        node_id: str | None = None,
        paper_id: str | None = None,
        kind: ReferenceEdgeKind | None = None,
        limit: int = 25,
    ) -> ReferenceNeighborhood:
        """Return papers linked to a Product KG node or to a paper.

        Parameters
        ----------
        node_id : str or None, optional
            Product KG node (e.g. ``job_type:protein-prepare``).
        paper_id : str or None, optional
            Paper id. Give ``node_id`` or ``paper_id``.
        kind : str or None, optional
            Keep only one edge kind (``cites``, ``method_of``, ``uses_tool``,
            ``compares``, ``describes``).
        limit : int, optional
            Edges to return (1-50).

        Returns
        -------
        ReferenceNeighborhood
            Center, edges, papers, and provenance.
        """
        params: dict[str, Any] = {"limit": limit}
        for key, value in (
            ("node_id", node_id),
            ("paper_id", paper_id),
            ("kind", kind),
        ):
            if value is not None:
                params[key] = value
        data = await self._http.request(
            "GET", ROUTES["reference_neighborhood"], params=params
        )
        return ReferenceNeighborhood.model_validate(data)
