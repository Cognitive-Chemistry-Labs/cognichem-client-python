"""RFC 7807 problem-detail errors for the CogniChem API."""

from __future__ import annotations

from typing import Any


class CogniChemError(Exception):
    """Base error for CogniChem client failures.

    Parameters
    ----------
    message : str
        Human-readable error summary (also used as the exception message).
    status : int or None, optional
        HTTP status code when the error came from an API response.
    type : str or None, optional
        RFC 7807 problem ``type`` URI.
    title : str or None, optional
        RFC 7807 problem ``title``.
    detail : str or None, optional
        RFC 7807 problem ``detail`` string.
    request_id : str or None, optional
        Correlating request identifier from the API.
    errors : list or None, optional
        Validation error list (typically present on HTTP 422).
    code : str, optional
        Stable client-side error code (e.g. ``api-key-limit-exceeded``).
    body : any, optional
        Raw parsed response body for debugging.

    Attributes
    ----------
    message : str
        Human-readable error summary.
    status : int or None
        HTTP status code, if any.
    type : str or None
        Problem type URI, if any.
    title : str or None
        Problem title, if any.
    detail : str or None
        Problem detail, if any.
    request_id : str or None
        Request identifier, if any.
    errors : list or None
        Validation errors, if any.
    code : str
        Stable client-side error code.
    body : any
        Raw response body, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        type: str | None = None,
        title: str | None = None,
        detail: str | None = None,
        request_id: str | None = None,
        errors: list[Any] | None = None,
        code: str = "unknown",
        body: Any = None,
    ) -> None:
        """Store problem-detail fields on the exception instance.

        Parameters
        ----------
        message : str
            Human-readable error summary.
        status : int or None, optional
            HTTP status code when available.
        type : str or None, optional
            RFC 7807 problem ``type`` URI.
        title : str or None, optional
            RFC 7807 problem ``title``.
        detail : str or None, optional
            RFC 7807 problem ``detail``.
        request_id : str or None, optional
            Correlating request identifier.
        errors : list or None, optional
            Validation error list when present.
        code : str, optional
            Stable client-side error code.
        body : any, optional
            Raw parsed response body.
        """
        super().__init__(message)
        self.message = message
        self.status = status
        self.type = type
        self.title = title
        self.detail = detail
        self.request_id = request_id
        self.errors = errors
        self.code = code
        self.body = body


class AuthenticationError(CogniChemError):
    """Raised for HTTP 401 Unauthorized responses.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


class ForbiddenError(CogniChemError):
    """Raised for HTTP 403 Forbidden responses.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


class NotFoundError(CogniChemError):
    """Raised for HTTP 404 Not Found responses.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


class ConflictError(CogniChemError):
    """Raised for HTTP 409 Conflict responses.

    Notes
    -----
    Common causes include idempotency-key reuse with a different body, or
    duplicate API key names. Inherits attributes from :class:`CogniChemError`.
    """


class ValidationError(CogniChemError):
    """Raised for HTTP 422 Unprocessable Entity responses.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`. Validation issue lists
    are often available on ``errors``.
    """


class RateLimitError(CogniChemError):
    """Raised for HTTP 429 Too Many Requests responses.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


class PollTimeoutError(CogniChemError):
    """Raised when a polling wait exceeds the configured timeout.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


class ProcessFailedError(CogniChemError):
    """Raised when a job, inference, or utility ends in ``error`` status.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


class ProcessCancelledError(CogniChemError):
    """Raised when a job ends in ``cancelled`` status.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


_API_KEY_LIMIT_SUFFIX = "/problems/api-key-limit-exceeded"
_DUPLICATE_NAME_DETAIL = "An API key with this name already exists"


def _is_record(value: Any) -> bool:
    """Return whether ``value`` is a mapping suitable for problem parsing.

    Parameters
    ----------
    value : any
        Candidate response body value.

    Returns
    -------
    bool
        ``True`` if ``value`` is a ``dict``.
    """
    return isinstance(value, dict)


def _read_detail(body: dict[str, Any]) -> str | None:
    """Extract a human-readable detail string from a problem body.

    Parameters
    ----------
    body : dict
        Parsed JSON error body.

    Returns
    -------
    str or None
        Best-effort message from ``detail``, validation ``msg`` fields,
        ``title``, or ``message``.
    """
    detail = body.get("detail")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail:
            if _is_record(item) and isinstance(item.get("msg"), str):
                parts.append(item["msg"])
        if parts:
            return "; ".join(parts)
    title = body.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    message = body.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()
    return None


def _error_code(status: int, body: dict[str, Any], message: str) -> str:
    """Map known API failures to stable client error codes.

    Parameters
    ----------
    status : int
        HTTP status code.
    body : dict
        Parsed JSON error body.
    message : str
        Resolved human-readable message.

    Returns
    -------
    str
        Client error code such as ``api-key-limit-exceeded``,
        ``duplicate-name``, or ``unknown``.
    """
    raw_type = body.get("type")
    problem_type = raw_type if isinstance(raw_type, str) else ""
    if status == 403 and problem_type.endswith(_API_KEY_LIMIT_SUFFIX):
        return "api-key-limit-exceeded"
    if status == 409 and message == _DUPLICATE_NAME_DETAIL:
        return "duplicate-name"
    return "unknown"


def _exception_class(status: int) -> type[CogniChemError]:
    """Choose a :class:`CogniChemError` subclass for an HTTP status.

    Parameters
    ----------
    status : int
        HTTP status code.

    Returns
    -------
    type of CogniChemError
        Exception class to raise.
    """
    if status == 401:
        return AuthenticationError
    if status == 403:
        return ForbiddenError
    if status == 404:
        return NotFoundError
    if status == 409:
        return ConflictError
    if status == 422:
        return ValidationError
    if status == 429:
        return RateLimitError
    return CogniChemError


def raise_for_problem(
    status: int,
    body: Any,
    *,
    fallback_message: str = "Request failed",
) -> None:
    """Raise a typed :class:`CogniChemError` from an HTTP error response body.

    Parameters
    ----------
    status : int
        HTTP status code.
    body : any
        Parsed JSON body or raw text.
    fallback_message : str, optional
        Message used when the body has no usable detail.

    Raises
    ------
    CogniChemError
        Always raised (never returns). Subclass depends on ``status``.
    """
    if not _is_record(body):
        cls = _exception_class(status)
        raise cls(fallback_message, status=status, body=body)

    message = _read_detail(body) or fallback_message
    code = _error_code(status, body, message)
    problem_type = body.get("type") if isinstance(body.get("type"), str) else None
    title = body.get("title") if isinstance(body.get("title"), str) else None
    detail = body.get("detail") if isinstance(body.get("detail"), str) else message
    request_id = (
        body.get("request_id") if isinstance(body.get("request_id"), str) else None
    )
    errors = body.get("errors") if isinstance(body.get("errors"), list) else None
    if status == 422 and errors is None and isinstance(body.get("detail"), list):
        errors = body["detail"]

    cls = _exception_class(status)
    raise cls(
        message,
        status=status,
        type=problem_type,
        title=title,
        detail=detail if isinstance(detail, str) else message,
        request_id=request_id,
        errors=errors,
        code=code,
        body=body,
    )
