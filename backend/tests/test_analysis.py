"""
Tests for the AI analysis service and endpoint.

Covers:
  - MockProvider pattern matching (OOMKill, CPU, deploy, queue, network, default)
  - IncidentContext prompt text generation
  - Confidence scoring scales with alert count
  - Timeline construction order
  - POST /incidents/{id}/analyze endpoint (full integration)
  - Analysis results persisted to Incident record
  - WS broadcast triggered after analysis
  - 404 for unknown incident
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.incident import create_incident, get_incident
from app.schemas.incident import IncidentCreate
from app.services.ai_service import (
    IncidentContext,
    MockProvider,
    RCAResult,
    _duration_str,
)

_NOW = datetime.now(tz=timezone.utc)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_ctx(
    title: str = "Test Incident",
    alerts: list[dict] | None = None,
    services: list[str] | None = None,
) -> IncidentContext:
    return IncidentContext(
        incident_id=1,
        title=title,
        severity="high",
        status="investigating",
        affected_services=services or ["orders-service"],
        existing_summary=None,
        alerts=alerts or [],
        events=[],
    )


def _alert(title: str, source: str = "datadog", severity: str = "high") -> dict:
    return {
        "id": 1,
        "source": source,
        "severity": severity,
        "title": title,
        "description": title,
        "service_name": "orders-service",
        "environment": "production",
        "timestamp": _NOW.isoformat(),
        "status": "open",
    }


async def _seed_incident(db: AsyncSession, title: str = "Test", org_id: int = 1) -> int:
    inc = await create_incident(
        db,
        IncidentCreate(
            title=title,
            severity="high",
            status="open",
            affected_services=["orders-service"],
        ),
        org_id=org_id,
    )
    return inc.id


# ─────────────────────────────────────────────
# Unit tests — MockProvider
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_oom_pattern():
    """OOMKill keywords should trigger the memory-leak template."""
    ctx = _make_ctx(
        title="OOMKilled pod",
        alerts=[_alert("OOMKilled: inventory-service pod restarted 8 times")],
    )
    result = await MockProvider().analyze(ctx)
    assert "memory" in result.root_cause.lower() or "oom" in result.root_cause.lower()
    assert result.confidence >= 0.8
    assert result.risk_level == "critical"


@pytest.mark.asyncio
async def test_mock_cpu_pattern():
    """CPU / utilisation keywords should trigger CPU saturation template."""
    ctx = _make_ctx(
        title="CPU spike",
        alerts=[_alert("RDS CPU Utilisation > 95%", source="aws")],
    )
    result = await MockProvider().analyze(ctx)
    assert "cpu" in result.root_cause.lower() or "query" in result.root_cause.lower()
    assert result.risk_level == "high"


@pytest.mark.asyncio
async def test_mock_deployment_pattern():
    """Deploy keywords trigger the bad-deployment template."""
    ctx = _make_ctx(
        title="Deploy failure",
        alerts=[_alert("Deploy workflow: user-service v2.16.0 rollout failed", source="github_actions")],
    )
    result = await MockProvider().analyze(ctx)
    assert "deploy" in result.root_cause.lower() or "rollback" in result.root_cause.lower()
    assert len(result.remediation_steps) > 0
    assert any("rollout undo" in s or "rollback" in s.lower() for s in result.remediation_steps)


@pytest.mark.asyncio
async def test_mock_queue_pattern():
    """DLQ / queue keywords trigger queue-backlog template."""
    ctx = _make_ctx(
        title="Queue backlog",
        alerts=[_alert("SQS Dead-Letter Queue depth > 100 messages", source="aws")],
    )
    result = await MockProvider().analyze(ctx)
    assert "consumer" in result.root_cause.lower() or "queue" in result.root_cause.lower()


@pytest.mark.asyncio
async def test_mock_network_pattern():
    """Network / AZ / partition keywords trigger network template."""
    ctx = _make_ctx(
        title="Network partition",
        alerts=[_alert("VPC 100% packet loss between AZs", source="aws")],
    )
    result = await MockProvider().analyze(ctx)
    assert "network" in result.root_cause.lower() or "connectivity" in result.root_cause.lower()
    assert result.risk_level == "critical"


@pytest.mark.asyncio
async def test_mock_default_fallback():
    """Unrecognised alert titles should fall back to default template."""
    ctx = _make_ctx(
        title="Mysterious widget anomaly",
        alerts=[_alert("Widget subsystem emitting unusual telemetry")],
    )
    result = await MockProvider().analyze(ctx)
    assert result.confidence < 0.7
    assert result.root_cause != ""
    assert len(result.remediation_steps) > 0


@pytest.mark.asyncio
async def test_mock_confidence_scales_with_alerts():
    """More alerts → higher confidence (up to 0.95 cap)."""
    few_alerts_ctx = _make_ctx(alerts=[_alert("OOMKilled")])
    many_alerts_ctx = _make_ctx(
        alerts=[_alert("OOMKilled pod") for _ in range(6)]
    )
    few_result = await MockProvider().analyze(few_alerts_ctx)
    many_result = await MockProvider().analyze(many_alerts_ctx)
    assert many_result.confidence >= few_result.confidence


@pytest.mark.asyncio
async def test_mock_timeline_ordered():
    """Timeline entries must be in ascending timestamp order."""
    ctx = _make_ctx(
        alerts=[
            {**_alert("Later alert"), "timestamp": "2026-01-01T10:30:00+00:00"},
            {**_alert("Earlier alert"), "timestamp": "2026-01-01T10:00:00+00:00"},
            {**_alert("Middle alert"), "timestamp": "2026-01-01T10:15:00+00:00"},
        ]
    )
    result = await MockProvider().analyze(ctx)
    timestamps = [e.timestamp for e in result.timeline]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_mock_remediation_interpolates_service():
    """Remediation steps should contain the primary service name."""
    ctx = _make_ctx(
        title="OOMKill cascade",
        alerts=[_alert("OOMKilled pod")],
        services=["inventory-service"],
    )
    result = await MockProvider().analyze(ctx)
    # At least one step should reference the service
    combined = " ".join(result.remediation_steps)
    assert "inventory-service" in combined


@pytest.mark.asyncio
async def test_mock_no_empty_fields():
    """Every field in RCAResult should be populated."""
    ctx = _make_ctx(alerts=[_alert("CPU spike")])
    result = await MockProvider().analyze(ctx)
    assert result.summary
    assert result.root_cause
    assert result.remediation_steps
    assert 0 <= result.confidence <= 1
    assert result.risk_level in {"low", "medium", "high", "critical"}
    assert result.provider == "mock"


def test_duration_str_single_alert():
    assert _duration_str([{"timestamp": "2026-01-01T10:00:00+00:00"}]) == "a short window"


def test_duration_str_minutes():
    alerts = [
        {"timestamp": "2026-01-01T10:00:00+00:00"},
        {"timestamp": "2026-01-01T10:25:00+00:00"},
    ]
    assert "minute" in _duration_str(alerts)


def test_context_prompt_text_contains_key_fields():
    ctx = _make_ctx(
        title="Big outage",
        alerts=[_alert("RDS CPU spike", source="aws")],
    )
    prompt = ctx.as_prompt_text()
    assert "Big outage" in prompt
    assert "AWS" in prompt
    assert "orders-service" in prompt


# ─────────────────────────────────────────────
# Integration tests — API endpoint
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_endpoint_returns_correct_structure(
    client: AsyncClient, db_session: AsyncSession
):
    """POST /analyze should return a well-formed AnalyzeResponse."""
    inc_id = await _seed_incident(db_session, "Analyze me")
    response = await client.post(f"/api/v1/incidents/{inc_id}/analyze")
    assert response.status_code == 200

    data = response.json()
    assert data["incident_id"] == inc_id
    assert "analysis" in data
    analysis = data["analysis"]

    # All required fields present
    for field in ["summary", "root_cause", "timeline", "remediation_steps", "confidence", "risk_level"]:
        assert field in analysis, f"Missing field: {field}"

    assert isinstance(analysis["timeline"], list)
    assert isinstance(analysis["remediation_steps"], list)
    assert 0.0 <= analysis["confidence"] <= 1.0
    assert analysis["risk_level"] in {"low", "medium", "high", "critical"}


@pytest.mark.asyncio
async def test_analyze_persists_results_to_incident(
    client: AsyncClient, db_session: AsyncSession
):
    """Analysis results must be saved back to the Incident record."""
    inc_id = await _seed_incident(db_session, "Persist test")
    await client.post(f"/api/v1/incidents/{inc_id}/analyze")

    incident = await get_incident(db_session, inc_id)
    assert incident.root_cause is not None and len(incident.root_cause) > 0
    assert incident.summary is not None and len(incident.summary) > 0
    assert incident.remediation_steps is not None
    assert len(incident.remediation_steps) > 0


@pytest.mark.asyncio
async def test_analyze_records_ai_analysis_event(
    client: AsyncClient, db_session: AsyncSession
):
    """An ai_analysis IncidentEvent should be recorded after analysis."""
    inc_id = await _seed_incident(db_session, "Event test")
    await client.post(f"/api/v1/incidents/{inc_id}/analyze")

    incident = await get_incident(db_session, inc_id)
    ai_events = [e for e in incident.events if e.event_type.value == "ai_analysis"]
    assert len(ai_events) >= 1
    assert "confidence" in ai_events[-1].message.lower()


@pytest.mark.asyncio
async def test_analyze_404_for_missing_incident(client: AsyncClient):
    """Analysing a non-existent incident should return 404."""
    response = await client.post("/api/v1/incidents/999999/analyze")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_analyze_reports_alerts_and_events_count(
    client: AsyncClient, db_session: AsyncSession
):
    """Response should include accurate counts of analyzed data."""
    inc_id = await _seed_incident(db_session, "Count test")
    response = await client.post(f"/api/v1/incidents/{inc_id}/analyze")
    data = response.json()
    assert "alerts_analyzed" in data
    assert "events_analyzed" in data
    assert isinstance(data["alerts_analyzed"], int)
    assert isinstance(data["events_analyzed"], int)


@pytest.mark.asyncio
async def test_analyze_uses_mock_provider_without_api_key(
    client: AsyncClient, db_session: AsyncSession
):
    """Without an API key the response should come from the mock provider."""
    inc_id = await _seed_incident(db_session, "Mock provider test")
    response = await client.post(f"/api/v1/incidents/{inc_id}/analyze")
    analysis = response.json()["analysis"]
    assert analysis["provider"] == "mock"


@pytest.mark.asyncio
async def test_analyze_ws_broadcast_fires(
    client: AsyncClient, db_session: AsyncSession
):
    """WebSocket broadcast should be called after a successful analysis."""
    inc_id = await _seed_incident(db_session, "WS broadcast test")
    with patch(
        "app.api.v1.analysis.ws_manager.emit_incident_updated",
        new_callable=AsyncMock,
    ) as mock_broadcast:
        response = await client.post(f"/api/v1/incidents/{inc_id}/analyze")
        assert response.status_code == 200
        mock_broadcast.assert_called_once()
        call_kwargs = mock_broadcast.call_args[1]
        assert "root_cause" in call_kwargs["changed_fields"]
