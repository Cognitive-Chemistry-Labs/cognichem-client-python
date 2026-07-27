from __future__ import annotations

import pytest

from cognichem_client.errors import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    RateLimitError,
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
