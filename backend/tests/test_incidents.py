"""Tests for the Incident CRUD API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.incident import create_incident
from app.schemas.incident import IncidentCreate

TEST_ORG_ID = 1  # matches conftest.py TEST_ORG_ID — must stay in sync


SAMPLE_INCIDENT = {
    "title": "Test Incident",
    "severity": "critical",
    "status": "open",
    "affected_services": ["orders-service", "orders-db"],
    "summary": "Test summary",
}


async def _seed_incident(db: AsyncSession, org_id: int = TEST_ORG_ID) -> int:
    incident = await create_incident(db, IncidentCreate(**SAMPLE_INCIDENT), org_id=org_id)
    return incident.id


@pytest.mark.asyncio
async def test_list_incidents_empty(client: AsyncClient):
    response = await client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_get_incident_by_id(client: AsyncClient, db_session: AsyncSession):
    incident_id = await _seed_incident(db_session)

    response = await client.get(f"/api/v1/incidents/{incident_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == incident_id
    assert data["title"] == "Test Incident"
    assert "events" in data


@pytest.mark.asyncio
async def test_get_incident_not_found(client: AsyncClient):
    response = await client.get("/api/v1/incidents/999999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_incident_status(client: AsyncClient, db_session: AsyncSession):
    incident_id = await _seed_incident(db_session)

    response = await client.patch(
        f"/api/v1/incidents/{incident_id}",
        json={"status": "investigating"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "investigating"

    # Should have auto-created a status_changed event
    events = data["events"]
    status_events = [e for e in events if e["event_type"] == "status_changed"]
    assert len(status_events) >= 1


@pytest.mark.asyncio
async def test_patch_incident_root_cause(client: AsyncClient, db_session: AsyncSession):
    incident_id = await _seed_incident(db_session)

    root_cause = "Memory leak in inventory-service v3.8.1"
    response = await client.patch(
        f"/api/v1/incidents/{incident_id}",
        json={"root_cause": root_cause},
    )
    assert response.status_code == 200
    assert response.json()["root_cause"] == root_cause

    # Should have auto-created an ai_analysis event
    events = response.json()["events"]
    ai_events = [e for e in events if e["event_type"] == "ai_analysis"]
    assert len(ai_events) >= 1


@pytest.mark.asyncio
async def test_filter_incidents_by_status(client: AsyncClient, db_session: AsyncSession):
    incident_id = await _seed_incident(db_session)
    await client.patch(f"/api/v1/incidents/{incident_id}", json={"status": "resolved"})

    response = await client.get("/api/v1/incidents?status=resolved")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(i["status"] == "resolved" for i in items)
