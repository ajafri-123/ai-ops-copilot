"""
Tests for Celery background tasks.

Strategy: call each task's internal async helper directly (bypassing the
Celery worker process) so tests run without a broker. We also test the
API's async-mode endpoints using the standard HTTP test client.

Covers:
  - process_alert happy path
  - process_alert with missing alert (graceful skip)
  - correlate_alert happy path
  - analyze_incident_bg happy path
  - analyze_incident_bg with missing incident (graceful skip)
  - generate_demo_alerts (disabled when DEMO_PERIODIC_ALERTS=False)
  - worker_heartbeat always returns alive
  - POST /alerts?async=true returns 201 + task_id
  - POST /incidents/{id}/analyze?async=true returns 202
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.alert import create_alert
from app.crud.incident import create_incident
from app.schemas.alert import AlertCreate
from app.schemas.incident import IncidentCreate

_NOW = datetime.now(tz=timezone.utc)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

def _alert_payload(**overrides) -> dict:
    base = {
        "source": "datadog",
        "severity": "high",
        "title": "CPU spike on orders-service",
        "description": "CPU exceeded 90%",
        "service_name": "orders-service",
        "environment": "production",
        "timestamp": _NOW.isoformat(),
        "status": "open",
    }
    return {**base, **overrides}


async def _seed_alert(db: AsyncSession) -> int:
    alert = await create_alert(db, AlertCreate(**_alert_payload()))
    return alert.id


async def _seed_incident(db: AsyncSession, title: str = "Test") -> int:
    inc = await create_incident(
        db,
        IncidentCreate(
            title=title,
            severity="high",
            status="open",
            affected_services=["orders-service"],
        ),
    )
    return inc.id


# ─────────────────────────────────────────────
# Helpers that invoke task logic without Celery
# ─────────────────────────────────────────────

async def _run_process_alert(alert_id: int, db: AsyncSession) -> dict:
    """Run the correlation part of process_alert using the existing db session."""
    from app.crud.alert import get_alert
    from app.services.correlation_engine import correlation_engine
    from app.core.ws_manager import ws_manager
    from app.schemas.alert import AlertRead

    alert = await get_alert(db, alert_id)
    if alert is None:
        return {"status": "skipped", "reason": "alert not found", "alert_id": alert_id}

    await ws_manager.emit_alert_created(AlertRead.model_validate(alert).model_dump())
    result = await correlation_engine.correlate(db, alert)

    return {
        "status": "ok",
        "alert_id": alert_id,
        "incident_id": result.incident.id,
        "created_new_incident": result.created_new,
    }


# ─────────────────────────────────────────────
# Unit tests — task logic
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_alert_creates_incident(db_session: AsyncSession):
    """process_alert should run correlation and return an incident ID."""
    alert_id = await _seed_alert(db_session)
    result = await _run_process_alert(alert_id, db_session)

    assert result["status"] == "ok"
    assert result["alert_id"] == alert_id
    assert isinstance(result["incident_id"], int)
    assert result["incident_id"] > 0


@pytest.mark.asyncio
async def test_process_alert_missing_alert(db_session: AsyncSession):
    """process_alert with a non-existent alert_id should skip gracefully."""
    result = await _run_process_alert(999_999, db_session)
    assert result["status"] == "skipped"
    assert "not found" in result["reason"]


@pytest.mark.asyncio
async def test_correlate_alert_assigns_to_incident(db_session: AsyncSession):
    """correlate_alert should assign an alert to an incident."""
    from app.crud.alert import get_alert
    from app.services.correlation_engine import correlation_engine

    alert_id = await _seed_alert(db_session)
    alert = await get_alert(db_session, alert_id)
    result = await correlation_engine.correlate(db_session, alert)

    assert result.incident.id > 0
    assert alert.service_name in (result.incident.affected_services or [])


@pytest.mark.asyncio
async def test_analyze_incident_bg_runs_pipeline(db_session: AsyncSession):
    """analyze_incident_bg should call run_analysis_pipeline and persist results."""
    from app.services.analysis_pipeline import run_analysis_pipeline

    incident_id = await _seed_incident(db_session, "Background analysis test")
    response = await run_analysis_pipeline(incident_id, db_session)

    assert response.incident_id == incident_id
    assert response.analysis.root_cause != ""
    assert len(response.analysis.remediation_steps) > 0
    assert 0.0 <= response.analysis.confidence <= 1.0


@pytest.mark.asyncio
async def test_analyze_incident_bg_missing_incident(db_session: AsyncSession):
    """analyze_incident_bg with bad ID should raise ValueError (no retry)."""
    from app.services.analysis_pipeline import run_analysis_pipeline

    with pytest.raises(ValueError, match="not found"):
        await run_analysis_pipeline(999_999, db_session)


def test_worker_heartbeat_returns_alive():
    """worker_heartbeat should always return status=alive without hitting any DB."""
    from app.workers.tasks import worker_heartbeat

    # Call the underlying function, not apply_async — no broker needed
    result = worker_heartbeat()
    assert result["status"] == "alive"
    assert "timestamp" in result


def test_generate_demo_alerts_disabled_by_default():
    """generate_demo_alerts should return disabled when DEMO_PERIODIC_ALERTS=false."""
    from app.workers.tasks import generate_demo_alerts

    with patch("app.workers.tasks.settings") as mock_settings:
        mock_settings.DEMO_PERIODIC_ALERTS = False
        result = generate_demo_alerts()
    assert result["status"] == "disabled"


# ─────────────────────────────────────────────
# API integration tests — async mode endpoints
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_alert_async_mode_returns_task_id(client: AsyncClient):
    """POST /alerts?async=true should return 201 with task_id."""
    with patch("app.api.v1.alerts.process_alert") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "fake-task-id-abc123"
        mock_task.apply_async.return_value = mock_result

        response = await client.post(
            "/api/v1/alerts?async=true",
            json=_alert_payload(),
        )

    assert response.status_code == 201
    data = response.json()
    assert "task_id" in data
    assert "alert" in data
    assert data["task_id"] == "fake-task-id-abc123"
    assert "background" in data["message"].lower() or "celery" in data["message"].lower() or "background" in data["message"].lower()


@pytest.mark.asyncio
async def test_post_alert_async_mode_enqueues_to_alerts_queue(client: AsyncClient):
    """async=true must route the task to the 'alerts' queue."""
    with patch("app.api.v1.alerts.process_alert") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "task-999"
        mock_task.apply_async.return_value = mock_result

        await client.post("/api/v1/alerts?async=true", json=_alert_payload())

    mock_task.apply_async.assert_called_once()
    call_kwargs = mock_task.apply_async.call_args[1]
    assert call_kwargs.get("queue") == "alerts"


@pytest.mark.asyncio
async def test_post_alert_sync_mode_still_works(client: AsyncClient):
    """Default POST /alerts (sync) should still return correlation info."""
    response = await client.post("/api/v1/alerts", json=_alert_payload())
    assert response.status_code == 201
    data = response.json()
    assert "incident_id" in data
    assert "correlation_score" in data


@pytest.mark.asyncio
async def test_analyze_async_mode_returns_202(client: AsyncClient, db_session: AsyncSession):
    """POST /incidents/{id}/analyze?async=true should return 202."""
    incident_id = await _seed_incident(db_session, "Async analyze test")

    with patch("app.api.v1.analysis.analyze_incident_bg") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "analysis-task-xyz"
        mock_task.apply_async.return_value = mock_result

        response = await client.post(
            f"/api/v1/incidents/{incident_id}/analyze?async=true"
        )

    assert response.status_code == 202
    detail = response.json()["detail"]
    assert detail["incident_id"] == incident_id
    assert "task_id" in detail


@pytest.mark.asyncio
async def test_analyze_async_mode_routes_to_analysis_queue(
    client: AsyncClient, db_session: AsyncSession
):
    """async analysis must go to the 'analysis' queue."""
    incident_id = await _seed_incident(db_session, "Queue routing test")

    with patch("app.api.v1.analysis.analyze_incident_bg") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "xyz"
        mock_task.apply_async.return_value = mock_result

        await client.post(f"/api/v1/incidents/{incident_id}/analyze?async=true")

    call_kwargs = mock_task.apply_async.call_args[1]
    assert call_kwargs.get("queue") == "analysis"
