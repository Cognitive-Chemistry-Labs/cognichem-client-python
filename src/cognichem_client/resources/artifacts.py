"""Durable artifact resource clients under ``/artifacts``."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from cognichem_client._http import AsyncHttpClient, HttpClient, ensure_idempotency_key
from cognichem_client.constants import ROUTES
from cognichem_client.resources.jobs import _maybe_save
from cognichem_client.types import (
    Artifact,
    ArtifactListResponse,
    ArtifactUsage,
    BinaryResult,
    MessageResponse,
)

UploadMode = Literal["cognichem_zip", "raw_file"]


def artifact_ref(
    artifact_id: str, port: str, *, records: Sequence[str] | None = None
) -> dict[str, Any]:
    """Build an ``$artifact`` reference for workflow params or job payloads.

    Parameters
    ----------
    artifact_id : str
        Artifact identifier.
    port : str
        Manifest port to bind (e.g. ``structure``, ``poses``).
    records : sequence of str or None, optional
        Keep only these manifest record ids.

    Returns
    -------
    dict
        ``{"$artifact": {"id": ..., "port": ..., "records"?: [...]}}``.

    Examples
    --------
    >>> artifact_ref("art-1", "structure")
    {'$artifact': {'id': 'art-1', 'port': 'structure'}}
    """
    ref: dict[str, Any] = {"id": artifact_id, "port": port}
    if records is not None:
        ref["records"] = list(records)
    return {"$artifact": ref}


def _list_params(
    *,
    limit: int | None,
    offset: int | None,
    data_kind: str | None,
    data_format: str | None,
    run_id: str | None,
    include_archive: bool,
) -> dict[str, Any] | None:
    """Build ``GET /artifacts`` query parameters, dropping unset values.

    Parameters
    ----------
    limit, offset : int or None
        Pagination.
    data_kind, data_format, run_id : str or None
        Filters.
    include_archive : bool
        Whether to include ``archive`` ports.

    Returns
    -------
    dict or None
        Query parameters, or ``None`` when nothing is set.
    """
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "data_kind": data_kind,
        "data_format": data_format,
        "run_id": run_id,
    }
    if include_archive:
        params["include_archive"] = "true"
    return {k: v for k, v in params.items() if v is not None} or None


def _upload_parts(
    file: str | Path | bytes,
    *,
    filename: str | None,
    mode: UploadMode | None,
    data_kind: str | None,
    data_format: str | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Build multipart ``files`` and form ``data`` for ``POST /artifacts``.

    Parameters
    ----------
    file : str or Path or bytes
        File path or raw bytes.
    filename : str or None
        Upload filename (defaults to the path name, or ``upload`` / ``.zip``).
    mode : {"cognichem_zip", "raw_file"} or None
        Upload mode; inferred when ``None`` (``raw_file`` when ``data_kind``
        is set, otherwise ``cognichem_zip``).
    data_kind, data_format : str or None
        Required for ``raw_file`` (e.g. ``protein_structure`` / ``pdb``).

    Returns
    -------
    tuple of (dict, dict)
        httpx ``files`` and ``data`` arguments.

    Raises
    ------
    ValueError
        If ``raw_file`` is missing ``data_kind`` or ``data_format``.
    """
    if isinstance(file, bytes):
        content = file
        name = filename
    else:
        path = Path(file)
        content = path.read_bytes()
        name = filename or path.name
    resolved_mode = mode or ("raw_file" if data_kind else "cognichem_zip")
    if resolved_mode == "raw_file" and not (data_kind and data_format):
        raise ValueError("raw_file uploads need data_kind and data_format")
    name = name or ("result.zip" if resolved_mode == "cognichem_zip" else "upload")
    data: dict[str, str] = {"mode": resolved_mode}
    if data_kind:
        data["data_kind"] = data_kind
    if data_format:
        data["data_format"] = data_format
    return {"file": (name, content)}, data


class ArtifactsResource:
    """Synchronous artifact endpoints under ``/artifacts``.

    Artifacts are durable job / workflow outputs described by a manifest of
    ports and records. Bind them into workflow params or job payloads with
    :func:`artifact_ref`, and fetch single records with :meth:`download`
    ``record=`` instead of whole zips.

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

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        data_kind: str | None = None,
        data_format: str | None = None,
        run_id: str | None = None,
        include_archive: bool = False,
    ) -> ArtifactListResponse:
        """List owned artifacts, one item per chainable manifest port.

        Parameters
        ----------
        limit : int or None, optional
            Artifacts per page (1-100).
        offset : int or None, optional
            Page offset (use ``next_offset`` from the previous page).
        data_kind : str or None, optional
            Keep only ports of this kind (e.g. ``molecule_set``).
        data_format : str or None, optional
            Keep only ports of this format (e.g. ``sdf``).
        run_id : str or None, optional
            Keep only artifacts from this workflow run.
        include_archive : bool, optional
            Also list whole-zip ``archive`` ports.

        Returns
        -------
        ArtifactListResponse
            Page of artifact ports.
        """
        data = self._http.request(
            "GET",
            ROUTES["artifacts_list"],
            params=_list_params(
                limit=limit,
                offset=offset,
                data_kind=data_kind,
                data_format=data_format,
                run_id=run_id,
                include_archive=include_archive,
            ),
        )
        return ArtifactListResponse.model_validate(data)

    def usage(self) -> ArtifactUsage:
        """Return artifact storage usage against the tier quota.

        Returns
        -------
        ArtifactUsage
            Used bytes, quota, artifact count, and tier.
        """
        data = self._http.request("GET", ROUTES["artifacts_usage"])
        return ArtifactUsage.model_validate(data)

    def upload(
        self,
        file: str | Path | bytes,
        *,
        mode: UploadMode | None = None,
        data_kind: str | None = None,
        data_format: str | None = None,
        filename: str | None = None,
        idempotency_key: str | None = None,
    ) -> Artifact:
        """Upload a library artifact.

        Parameters
        ----------
        file : str or Path or bytes
            File path or raw bytes.
        mode : {"cognichem_zip", "raw_file"} or None, optional
            ``cognichem_zip`` for a CogniChem ``result.zip``; ``raw_file`` for
            an allowlisted PDB / SDF / SMILES file. Inferred when omitted
            (``raw_file`` if ``data_kind`` is given).
        data_kind : str or None, optional
            Required for ``raw_file`` (e.g. ``protein_structure``).
        data_format : str or None, optional
            Required for ``raw_file`` (e.g. ``pdb``).
        filename : str or None, optional
            Upload filename (defaults to the path name).
        idempotency_key : str or None, optional
            Idempotency key for safe retries. A random key is generated when
            omitted (API-key callers must send one).

        Returns
        -------
        Artifact
            The stored artifact and its manifest.

        Raises
        ------
        ValueError
            If ``raw_file`` is missing ``data_kind`` or ``data_format``.
        """
        files, form = _upload_parts(
            file,
            filename=filename,
            mode=mode,
            data_kind=data_kind,
            data_format=data_format,
        )
        data = self._http.request(
            "POST",
            ROUTES["artifacts_upload"],
            data=form,
            files=files,
            content_type=None,
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return Artifact.model_validate(data)

    def get(self, artifact_id: str) -> Artifact:
        """Fetch metadata and the parsed manifest of an owned artifact.

        Parameters
        ----------
        artifact_id : str
            Artifact identifier.

        Returns
        -------
        Artifact
            Metadata plus manifest (ports and records).
        """
        data = self._http.request(
            "GET", ROUTES["artifacts_get"].format(artifact_id=artifact_id)
        )
        return Artifact.model_validate(data)

    def download(
        self,
        artifact_id: str,
        *,
        record: str | None = None,
        port: str | None = None,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        """Download a whole artifact zip, or one manifest record.

        Parameters
        ----------
        artifact_id : str
            Artifact identifier.
        record : str or None, optional
            Manifest record id to fetch alone. Required for virtual artifacts.
        port : str or None, optional
            Port that scopes ``record`` when the id is ambiguous.
        save_path : str or Path or None, optional
            Optional file or directory path to write the bytes.

        Returns
        -------
        BinaryResult
            Content bytes plus filename and media type.
        """
        params = {k: v for k, v in {"record": record, "port": port}.items() if v}
        result = self._http.request(
            "GET",
            ROUTES["artifacts_download"].format(artifact_id=artifact_id),
            params=params or None,
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    def delete(self, artifact_id: str) -> MessageResponse:
        """Delete an owned artifact and its stored files.

        Parameters
        ----------
        artifact_id : str
            Artifact identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = self._http.request(
            "DELETE", ROUTES["artifacts_delete"].format(artifact_id=artifact_id)
        )
        return MessageResponse.model_validate(data)


class AsyncArtifactsResource:
    """Asynchronous artifact endpoints under ``/artifacts``.

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

    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        data_kind: str | None = None,
        data_format: str | None = None,
        run_id: str | None = None,
        include_archive: bool = False,
    ) -> ArtifactListResponse:
        """List owned artifacts, one item per chainable manifest port.

        Parameters
        ----------
        limit : int or None, optional
            Artifacts per page (1-100).
        offset : int or None, optional
            Page offset (use ``next_offset`` from the previous page).
        data_kind : str or None, optional
            Keep only ports of this kind (e.g. ``molecule_set``).
        data_format : str or None, optional
            Keep only ports of this format (e.g. ``sdf``).
        run_id : str or None, optional
            Keep only artifacts from this workflow run.
        include_archive : bool, optional
            Also list whole-zip ``archive`` ports.

        Returns
        -------
        ArtifactListResponse
            Page of artifact ports.
        """
        data = await self._http.request(
            "GET",
            ROUTES["artifacts_list"],
            params=_list_params(
                limit=limit,
                offset=offset,
                data_kind=data_kind,
                data_format=data_format,
                run_id=run_id,
                include_archive=include_archive,
            ),
        )
        return ArtifactListResponse.model_validate(data)

    async def usage(self) -> ArtifactUsage:
        """Return artifact storage usage against the tier quota.

        Returns
        -------
        ArtifactUsage
            Used bytes, quota, artifact count, and tier.
        """
        data = await self._http.request("GET", ROUTES["artifacts_usage"])
        return ArtifactUsage.model_validate(data)

    async def upload(
        self,
        file: str | Path | bytes,
        *,
        mode: UploadMode | None = None,
        data_kind: str | None = None,
        data_format: str | None = None,
        filename: str | None = None,
        idempotency_key: str | None = None,
    ) -> Artifact:
        """Upload a library artifact.

        Parameters
        ----------
        file : str or Path or bytes
            File path or raw bytes.
        mode : {"cognichem_zip", "raw_file"} or None, optional
            Upload mode; inferred when omitted (``raw_file`` if ``data_kind``
            is given).
        data_kind : str or None, optional
            Required for ``raw_file`` (e.g. ``protein_structure``).
        data_format : str or None, optional
            Required for ``raw_file`` (e.g. ``pdb``).
        filename : str or None, optional
            Upload filename (defaults to the path name).
        idempotency_key : str or None, optional
            Idempotency key for safe retries. A random key is generated when
            omitted (API-key callers must send one).

        Returns
        -------
        Artifact
            The stored artifact and its manifest.

        Raises
        ------
        ValueError
            If ``raw_file`` is missing ``data_kind`` or ``data_format``.
        """
        files, form = _upload_parts(
            file,
            filename=filename,
            mode=mode,
            data_kind=data_kind,
            data_format=data_format,
        )
        data = await self._http.request(
            "POST",
            ROUTES["artifacts_upload"],
            data=form,
            files=files,
            content_type=None,
            idempotency_key=ensure_idempotency_key(idempotency_key),
        )
        return Artifact.model_validate(data)

    async def get(self, artifact_id: str) -> Artifact:
        """Fetch metadata and the parsed manifest of an owned artifact.

        Parameters
        ----------
        artifact_id : str
            Artifact identifier.

        Returns
        -------
        Artifact
            Metadata plus manifest (ports and records).
        """
        data = await self._http.request(
            "GET", ROUTES["artifacts_get"].format(artifact_id=artifact_id)
        )
        return Artifact.model_validate(data)

    async def download(
        self,
        artifact_id: str,
        *,
        record: str | None = None,
        port: str | None = None,
        save_path: str | Path | None = None,
    ) -> BinaryResult:
        """Download a whole artifact zip, or one manifest record.

        Parameters
        ----------
        artifact_id : str
            Artifact identifier.
        record : str or None, optional
            Manifest record id to fetch alone. Required for virtual artifacts.
        port : str or None, optional
            Port that scopes ``record`` when the id is ambiguous.
        save_path : str or Path or None, optional
            Optional file or directory path to write the bytes.

        Returns
        -------
        BinaryResult
            Content bytes plus filename and media type.
        """
        params = {k: v for k, v in {"record": record, "port": port}.items() if v}
        result = await self._http.request(
            "GET",
            ROUTES["artifacts_download"].format(artifact_id=artifact_id),
            params=params or None,
            expect_json=False,
        )
        assert isinstance(result, BinaryResult)
        return _maybe_save(result, save_path)

    async def delete(self, artifact_id: str) -> MessageResponse:
        """Delete an owned artifact and its stored files.

        Parameters
        ----------
        artifact_id : str
            Artifact identifier.

        Returns
        -------
        MessageResponse
            Server confirmation message.
        """
        data = await self._http.request(
            "DELETE", ROUTES["artifacts_delete"].format(artifact_id=artifact_id)
        )
        return MessageResponse.model_validate(data)
