"""Tests for the Alert CRUD API endpoints."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


SAMPLE_ALERT = {
    "source": "aws",
    "severity": "critical",
    "title": "RDS CPU > 95%",
    "description": "Aurora cluster CPU spiked.",
    "service_name": "orders-db",
    "environment": "production",
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "status": "open",
}


@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient):
    response = await client.post("/api/v1/alerts", json=SAMPLE_ALERT)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["source"] == "aws"
    assert data["severity"] == "critical"
    assert data["service_name"] == "orders-db"


@pytest.mark.asyncio
async def test_get_alerts_list(client: AsyncClient):
    # Create two alerts
    for title in ["Alert A", "Alert B"]:
        payload = {**SAMPLE_ALERT, "title": title}
        await client.post("/api/v1/alerts", json=payload)

    response = await client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_alert_by_id(client: AsyncClient):
    create_resp = await client.post("/api/v1/alerts", json=SAMPLE_ALERT)
    alert_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/alerts/{alert_id}")
    assert response.status_code == 200
    assert response.json()["id"] == alert_id


@pytest.mark.asyncio
async def test_get_alert_not_found(client: AsyncClient):
    response = await client.get("/api/v1/alerts/999999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_filter_alerts_by_status(client: AsyncClient):
    # Create one open + one resolved alert
    await client.post("/api/v1/alerts", json={**SAMPLE_ALERT, "status": "open"})
    await client.post("/api/v1/alerts", json={**SAMPLE_ALERT, "status": "resolved"})

    response = await client.get("/api/v1/alerts?status=resolved")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(i["status"] == "resolved" for i in items)


@pytest.mark.asyncio
async def test_filter_alerts_by_source(client: AsyncClient):
    await client.post("/api/v1/alerts", json={**SAMPLE_ALERT, "source": "datadog"})

    response = await client.get("/api/v1/alerts?source=datadog")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(i["source"] == "datadog" for i in items)
