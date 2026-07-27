"""RFC 7807 problem-detail errors for the CogniChem API."""

from __future__ import annotations

from typing import Any


class CogniChemError(Exception):
    """Base error for CogniChem client failures."""

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
    """401 Unauthorized."""


class ForbiddenError(CogniChemError):
    """403 Forbidden."""


class NotFoundError(CogniChemError):
    """404 Not Found."""


class ConflictError(CogniChemError):
    """409 Conflict (e.g. idempotency key reuse with different body)."""


class ValidationError(CogniChemError):
    """422 Unprocessable Entity."""


class RateLimitError(CogniChemError):
    """429 Too Many Requests."""


class PollTimeoutError(CogniChemError):
    """Polling wait exceeded the configured timeout."""


class ProcessFailedError(CogniChemError):
    """A job/inference/utility reached a failed terminal status."""


class ProcessCancelledError(CogniChemError):
    """A job was cancelled."""


_API_KEY_LIMIT_SUFFIX = "/problems/api-key-limit-exceeded"
_DUPLICATE_NAME_DETAIL = "An API key with this name already exists"


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _read_detail(body: dict[str, Any]) -> str | None:
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
    raw_type = body.get("type")
    problem_type = raw_type if isinstance(raw_type, str) else ""
    if status == 403 and problem_type.endswith(_API_KEY_LIMIT_SUFFIX):
        return "api-key-limit-exceeded"
    if status == 409 and message == _DUPLICATE_NAME_DETAIL:
        return "duplicate-name"
    return "unknown"


def _exception_class(status: int) -> type[CogniChemError]:
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
    """Raise a typed :class:`CogniChemError` from an HTTP error response body."""
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
