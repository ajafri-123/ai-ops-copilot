import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_health_endpoint_exists():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    # 200 if postgres+redis are up; 200 with degraded status if not
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "services" in body
