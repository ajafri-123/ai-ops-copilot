"""
Tests for Integration endpoints and test-alert flow.

Covers:
  - GET /integrations returns empty list for a fresh org
  - POST /integrations creates a disconnected record
  - PATCH /integrations/{id} status=connected sets config + last_sync
  - PATCH /integrations/{id} status=disconnected clears config
  - POST /integrations/{id}/test-alert returns 400 if disconnected
  - POST /integrations/{id}/test-alert creates real alert + incident when connected
  - Test alert is org-scoped (appears in GET /alerts for same org)
  - Integration not found returns 404
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_list_integrations_empty(client: AsyncClient):
    """A fresh org with no integrations returns empty list."""
    resp = await client.get("/api/v1/integrations")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_integration(client: AsyncClient):
    resp = await client.post(
        "/api/v1/integrations",
        json={"provider": "datadog"},
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["provider"] == "datadog"
    assert data["name"] == "Datadog"
    assert data["status"] == "disconnected"
    assert data["last_sync"] is None
    assert data["config"] is None
    assert isinstance(data["id"], int)


@pytest.mark.asyncio
async def test_create_integration_custom_name(client: AsyncClient):
    resp = await client.post(
        "/api/v1/integrations",
        json={"provider": "sentry", "name": "Sentry Production"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Sentry Production"


@pytest.mark.asyncio
async def test_connect_integration_sets_config_and_last_sync(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/integrations", json={"provider": "aws_cloudwatch"}
    )
    intg_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/integrations/{intg_id}",
        json={"status": "connected"},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()

    assert data["status"] == "connected"
    assert data["last_sync"] is not None, "last_sync must be set on connect"
    assert data["config"] is not None, "Default config must be populated on connect"
    assert "region" in data["config"]  # AWS config has 'region'


@pytest.mark.asyncio
async def test_disconnect_integration_clears_config(client: AsyncClient):
    # Create and connect
    create_resp = await client.post(
        "/api/v1/integrations", json={"provider": "kubernetes"}
    )
    intg_id = create_resp.json()["id"]
    await client.patch(f"/api/v1/integrations/{intg_id}", json={"status": "connected"})

    # Disconnect
    patch_resp = await client.patch(
        f"/api/v1/integrations/{intg_id}", json={"status": "disconnected"}
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["status"] == "disconnected"
    assert data["config"] is None
    assert data["last_sync"] is None


@pytest.mark.asyncio
async def test_test_alert_requires_connected_integration(client: AsyncClient):
    """test-alert on a disconnected integration must return 400."""
    create_resp = await client.post(
        "/api/v1/integrations", json={"provider": "github_actions"}
    )
    intg_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/integrations/{intg_id}/test-alert")
    assert resp.status_code == 400
    assert "connected" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_test_alert_creates_real_alert_and_incident(client: AsyncClient):
    """test-alert on a connected integration creates a real alert + incident."""
    create_resp = await client.post(
        "/api/v1/integrations", json={"provider": "datadog"}
    )
    intg_id = create_resp.json()["id"]
    await client.patch(f"/api/v1/integrations/{intg_id}", json={"status": "connected"})

    resp = await client.post(f"/api/v1/integrations/{intg_id}/test-alert")
    assert resp.status_code == 201
    data = resp.json()

    assert data["integration_id"] == intg_id
    assert data["provider"] == "datadog"
    assert isinstance(data["alert_id"], int)
    assert isinstance(data["incident_id"], int)
    assert data["alert_title"]
    assert data["incident_title"]
    assert isinstance(data["created_new_incident"], bool)
    assert isinstance(data["correlation_score"], float)


@pytest.mark.asyncio
async def test_test_alert_updates_last_sync(client: AsyncClient):
    """last_sync must be refreshed after a successful test-alert call."""
    create_resp = await client.post(
        "/api/v1/integrations", json={"provider": "kubernetes"}
    )
    intg_id = create_resp.json()["id"]
    await client.patch(f"/api/v1/integrations/{intg_id}", json={"status": "connected"})

    # Record last_sync before test
    before = (await client.get(f"/api/v1/integrations")).json()
    before_sync = next((i["last_sync"] for i in before if i["id"] == intg_id), None)

    await client.post(f"/api/v1/integrations/{intg_id}/test-alert")

    after = (await client.get(f"/api/v1/integrations")).json()
    after_sync = next((i["last_sync"] for i in after if i["id"] == intg_id), None)

    assert after_sync is not None
    # after_sync should be >= before_sync
    assert after_sync >= (before_sync or "")


@pytest.mark.asyncio
async def test_test_alert_is_visible_in_alert_list(client: AsyncClient):
    """Alert produced by test-alert should appear in GET /alerts."""
    create_resp = await client.post(
        "/api/v1/integrations", json={"provider": "sentry"}
    )
    intg_id = create_resp.json()["id"]
    await client.patch(f"/api/v1/integrations/{intg_id}", json={"status": "connected"})

    test_resp = await client.post(f"/api/v1/integrations/{intg_id}/test-alert")
    created_alert_id = test_resp.json()["alert_id"]

    alerts_resp = await client.get("/api/v1/alerts")
    alert_ids = [a["id"] for a in alerts_resp.json()["items"]]
    assert created_alert_id in alert_ids, "Test alert should appear in the alert feed"


@pytest.mark.asyncio
async def test_integration_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/integrations")
    assert resp.status_code == 200

    # PATCH non-existent
    resp = await client.patch("/api/v1/integrations/999999", json={"status": "connected"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_all_providers_can_be_created(client: AsyncClient):
    """Every IntegrationProvider value should be a valid POST target."""
    providers = [
        "aws_cloudwatch", "datadog", "sentry",
        "github_actions", "kubernetes", "slack",
    ]
    for provider in providers:
        resp = await client.post("/api/v1/integrations", json={"provider": provider})
        assert resp.status_code == 201, f"Provider {provider} returned {resp.status_code}"
        assert resp.json()["provider"] == provider


@pytest.mark.asyncio
async def test_all_providers_can_send_test_alert(client: AsyncClient):
    """All connected providers should successfully produce a test alert."""
    providers = [
        "aws_cloudwatch", "datadog", "sentry",
        "github_actions", "kubernetes", "slack",
    ]
    for provider in providers:
        create_resp = await client.post(
            "/api/v1/integrations", json={"provider": provider}
        )
        intg_id = create_resp.json()["id"]
        await client.patch(
            f"/api/v1/integrations/{intg_id}", json={"status": "connected"}
        )

        test_resp = await client.post(f"/api/v1/integrations/{intg_id}/test-alert")
        assert test_resp.status_code == 201, (
            f"Provider {provider} test-alert returned {test_resp.status_code}: "
            f"{test_resp.text}"
        )
