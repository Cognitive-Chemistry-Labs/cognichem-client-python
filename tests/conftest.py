from __future__ import annotations

import pytest

from cognichem_client import CogniChem
from cognichem_client.async_client import AsyncCogniChem

BASE_URL = "https://api.test.cognichem.com"


@pytest.fixture
def client() -> CogniChem:
    return CogniChem(api_key="test-key", base_url=BASE_URL)


@pytest.fixture
async def async_client() -> AsyncCogniChem:
    return AsyncCogniChem(api_key="test-key", base_url=BASE_URL)
