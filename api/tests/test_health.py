import pytest
from httpx import AsyncClient

from main import app


@pytest.mark.anyio
async def test_healthcheck_endpoint() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
