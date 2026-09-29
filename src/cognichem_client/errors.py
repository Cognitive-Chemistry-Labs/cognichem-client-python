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
    retryability : str or None, optional
        Server retry class: ``validation``, ``auth``, ``quota``, ``conflict``,
        ``upstream``, ``timeout``, or ``terminal``.

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
        Raw response body, if any. Problem extensions (for example
        ``cap_usd`` on ``session-spend-cap``, or ``proposal`` on
        ``estimate-changed``) live here.
    retryability : str or None
        Server retry class, if any.
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
        retryability: str | None = None,
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
        retryability : str or None, optional
            Server retry class.
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
        self.retryability = retryability


class BadRequestError(CogniChemError):
    """Raised for HTTP 400 Bad Request responses.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`. Operational failures
    such as ``missing-idempotency-key`` or ``insufficient_wallet`` on
    workflow run create arrive as 400.
    """


class AuthenticationError(CogniChemError):
    """Raised for HTTP 401 Unauthorized responses.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


class PaymentRequiredError(CogniChemError):
    """Raised for HTTP 402 Payment Required responses.

    Notes
    -----
    The wallet cannot cover the hold (``insufficient-wallet``). Inherits
    attributes from :class:`CogniChemError`.
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


class GoneError(CogniChemError):
    """Raised for HTTP 410 Gone responses.

    Notes
    -----
    Examples: an expired Assistant proposal (``proposal-expired``) or a
    ``?record=`` download whose parent artifact expired. Inherits attributes
    from :class:`CogniChemError`.
    """


class PayloadTooLargeError(CogniChemError):
    """Raised for HTTP 413 Content Too Large responses.

    Notes
    -----
    Examples: an upload over the size cap or storage quota, or a WorkflowSpec
    over the byte cap (Diagnostic list on ``errors``). Inherits attributes
    from :class:`CogniChemError`.
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


class ServerError(CogniChemError):
    """Raised for HTTP 5xx responses.

    Notes
    -----
    Usually safe to retry (``retryability`` is ``upstream`` or ``timeout``).
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

    Also raised when a workflow run ends in ``failed`` status.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


class ProcessCancelledError(CogniChemError):
    """Raised when a job or workflow run ends in ``cancelled`` status.

    Notes
    -----
    Inherits attributes from :class:`CogniChemError`.
    """


_PROBLEMS_SEGMENT = "/problems/"
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
        Client error code: ``duplicate-name``, the problem ``type`` slug
        (e.g. ``api-key-limit-exceeded``, ``missing-idempotency-key``,
        ``session-spend-cap``), or ``unknown`` for generic ``http-<status>``
        problems.
    """
    if status == 409 and message == _DUPLICATE_NAME_DETAIL:
        return "duplicate-name"
    raw_type = body.get("type")
    problem_type = raw_type if isinstance(raw_type, str) else ""
    if _PROBLEMS_SEGMENT in problem_type:
        slug = problem_type.rsplit(_PROBLEMS_SEGMENT, 1)[1].strip("/")
        if slug and not slug.startswith("http-"):
            return slug
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
    if status == 400:
        return BadRequestError
    if status == 401:
        return AuthenticationError
    if status == 402:
        return PaymentRequiredError
    if status == 403:
        return ForbiddenError
    if status == 404:
        return NotFoundError
    if status == 409:
        return ConflictError
    if status == 410:
        return GoneError
    if status == 413:
        return PayloadTooLargeError
    if status == 422:
        return ValidationError
    if status == 429:
        return RateLimitError
    if status >= 500:
        return ServerError
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
    retryability = (
        body.get("retryability") if isinstance(body.get("retryability"), str) else None
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
        retryability=retryability,
    )
