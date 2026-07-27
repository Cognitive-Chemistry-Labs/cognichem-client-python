from __future__ import annotations

import httpx
import pytest
import respx

from cognichem_client import AsyncCogniChem, CogniChem
from cognichem_client.errors import ValidationError

BASE = "https://api.test.cognichem.com"


@respx.mock
def test_utils_run() -> None:
    respx.post(f"{BASE}/api/v1/utils/submit").mock(
        return_value=httpx.Response(200, json={"process_id": "utl-1"})
    )
    respx.get(f"{BASE}/api/v1/utils/status").mock(
        return_value=httpx.Response(
            200, json={"process_id": "utl-1", "status": "completed", "message": None}
        )
    )
    respx.get(f"{BASE}/api/v1/utils/result").mock(
        return_value=httpx.Response(200, json={"data": {"pdb": "ATOM"}})
    )
    client = CogniChem(api_key="k", base_url=BASE)
    result = client.utils.run(
        "convert",
        {"input_data": "CCO", "input_format": "smiles", "output_format": "pdbblock"},
        poll_interval=0.01,
        timeout=2.0,
    )
    assert result.data["pdb"] == "ATOM"


@respx.mock
def test_inference_submit_batch_and_models() -> None:
    respx.post(f"{BASE}/api/v1/inference/submit-batch").mock(
        return_value=httpx.Response(200, json={"process_ids": ["inf-1", "inf-2"]})
    )
    respx.get(f"{BASE}/api/v1/public-models/mpnn").mock(
        return_value=httpx.Response(
            200, json={"model_names": ["Hydration free energy"]}
        )
    )
    respx.get(f"{BASE}/api/v1/user-models/mpnn").mock(
        return_value=httpx.Response(200, json={"model_names": ["mine"]})
    )
    respx.delete(f"{BASE}/api/v1/user-models/mpnn").mock(
        return_value=httpx.Response(200, json={"message": "deleted"})
    )

    client = CogniChem(api_key="k", base_url=BASE)
    batch = client.inference.submit_batch(
        [
            {
                "model_type": "mpnn",
                "model_name": "Hydration free energy",
                "payload": {"smiles": "CCO"},
            }
        ],
        idempotency_key="batch-1",
    )
    assert batch.process_ids == ["inf-1", "inf-2"]
    public_names = client.inference.models.mpnn.public()["model_names"]
    assert public_names[0].startswith("Hydration")
    assert client.inference.models.mpnn.user()["model_names"] == ["mine"]
    assert client.inference.models.mpnn.delete("mine").message == "deleted"


@respx.mock
def test_auth_login_and_api_keys_prefer_bearer() -> None:
    respx.post(f"{BASE}/api/v1/auth/login-email").mock(
        return_value=httpx.Response(
            200,
            json={
                "access_token": "jwt-access",
                "refresh_token": "jwt-refresh",
                "token_type": "bearer",
                "expires_in": 3600,
                "expires_at": 9999999999,
            },
        )
    )
    list_route = respx.get(f"{BASE}/api/v1/auth/api-keys").mock(
        return_value=httpx.Response(
            200,
            json={
                "keys": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "CI",
                        "key_prefix": "abcd",
                        "scopes": [],
                        "created_at": "2026-05-21T12:00:00Z",
                        "last_used_at": None,
                        "rotated_at": None,
                    }
                ],
                "limit": 5,
                "count": 1,
            },
        )
    )
    respx.get(f"{BASE}/api/v1/auth/check").mock(
        return_value=httpx.Response(200, json={"message": "You are authenticated!"})
    )
    respx.get(f"{BASE}/api/v1/usage-limits").mock(
        return_value=httpx.Response(
            200, json={"usage_limits": {"monthly_usage": 1, "monthly_limit": 100}}
        )
    )

    client = CogniChem(api_key="k", base_url=BASE)
    tokens = client.auth.login_email("user@example.com", "secret")
    assert tokens.access_token == "jwt-access"
    keys = client.api_keys.list()
    assert keys.count == 1
    assert list_route.calls.last.request.headers["Authorization"] == "Bearer jwt-access"
    assert "X-Api-Key" not in list_route.calls.last.request.headers
    assert client.auth.check().message == "You are authenticated!"
    assert client.usage.limits().usage_limits["monthly_limit"] == 100


@respx.mock
def test_problem_detail_from_http() -> None:
    respx.post(f"{BASE}/api/v1/jobs/submit").mock(
        return_value=httpx.Response(
            422,
            json={
                "type": "/api/v1/problems/http-422",
                "title": "Validation Error",
                "status": 422,
                "detail": "payload invalid",
            },
        )
    )
    client = CogniChem(api_key="k", base_url=BASE)
    with pytest.raises(ValidationError, match="payload invalid"):
        client.jobs.submit("n", "train-mpnn", {})


@respx.mock
@pytest.mark.asyncio
async def test_async_inference_run() -> None:
    respx.post(f"{BASE}/api/v1/inference/submit").mock(
        return_value=httpx.Response(200, json={"process_id": "inf-9"})
    )
    respx.get(f"{BASE}/api/v1/inference/status").mock(
        return_value=httpx.Response(
            200, json={"process_id": "inf-9", "status": "completed", "message": None}
        )
    )
    respx.get(f"{BASE}/api/v1/inference/result").mock(
        return_value=httpx.Response(200, json={"data": {"predictions": [1.2]}})
    )
    async with AsyncCogniChem(api_key="k", base_url=BASE) as client:
        result = await client.inference.run(
            "mpnn",
            "Hydration free energy",
            {"smiles": "CCO"},
            poll_interval=0.01,
            timeout=2.0,
        )
    assert result.data["predictions"] == [1.2]


def test_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COGNICHEM_API_KEY", "env-key")
    monkeypatch.setenv("COGNICHEM_BASE_URL", BASE)
    client = CogniChem.from_env()
    assert client._http.api_key == "env-key"
    assert client._http.base_url == BASE
