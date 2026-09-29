from __future__ import annotations

import pytest

from cognichem_client.errors import (
    AuthenticationError,
    BadRequestError,
    CogniChemError,
    ConflictError,
    ForbiddenError,
    GoneError,
    PayloadTooLargeError,
    PaymentRequiredError,
    RateLimitError,
    ServerError,
    ValidationError,
    raise_for_problem,
)


def test_raise_rfc7807_detail() -> None:
    with pytest.raises(AuthenticationError) as exc:
        raise_for_problem(
            401,
            {
                "type": "/api/v1/problems/http-401",
                "title": "Unauthorized",
                "status": 401,
                "detail": "Invalid API key",
                "request_id": "req-1",
            },
        )
    assert exc.value.message == "Invalid API key"
    assert exc.value.request_id == "req-1"


def test_api_key_limit_code() -> None:
    with pytest.raises(ForbiddenError) as exc:
        raise_for_problem(
            403,
            {
                "type": "/api/v1/problems/api-key-limit-exceeded",
                "detail": "Too many keys",
            },
        )
    assert exc.value.code == "api-key-limit-exceeded"


def test_duplicate_name_code() -> None:
    with pytest.raises(ConflictError) as exc:
        raise_for_problem(
            409,
            {"detail": "An API key with this name already exists"},
        )
    assert exc.value.code == "duplicate-name"


def test_validation_errors_list() -> None:
    with pytest.raises(ValidationError) as exc:
        raise_for_problem(
            422,
            {
                "detail": [
                    {"msg": "Field required", "loc": ["body", "job_name"]},
                    {"msg": "Invalid type", "loc": ["body", "payload"]},
                ]
            },
        )
    assert "Field required" in exc.value.message
    assert exc.value.errors is not None


def test_rate_limit() -> None:
    with pytest.raises(RateLimitError):
        raise_for_problem(429, {"detail": "Slow down"})


@pytest.mark.parametrize(
    ("status", "cls"),
    [
        (400, BadRequestError),
        (402, PaymentRequiredError),
        (410, GoneError),
        (413, PayloadTooLargeError),
        (503, ServerError),
    ],
)
def test_status_classes(status: int, cls: type[CogniChemError]) -> None:
    with pytest.raises(cls):
        raise_for_problem(status, {"detail": "nope"})


def test_problem_type_slug_code_and_retryability() -> None:
    with pytest.raises(BadRequestError) as exc:
        raise_for_problem(
            400,
            {
                "type": "/api/v1/problems/missing-idempotency-key",
                "title": "Missing Idempotency-Key",
                "status": 400,
                "detail": "Idempotency-Key is required for API-key mutations",
                "retryability": "validation",
            },
        )
    assert exc.value.code == "missing-idempotency-key"
    assert exc.value.retryability == "validation"


def test_generic_http_problem_code_is_unknown() -> None:
    with pytest.raises(CogniChemError) as exc:
        raise_for_problem(500, {"type": "/api/v1/problems/http-500", "detail": "x"})
    assert exc.value.code == "unknown"
