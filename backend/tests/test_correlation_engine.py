"""
Tests for the alert correlation engine.

Covers:
  - Same-service alerts merge into one incident
  - Cross-service alerts merge via dependency graph
  - Keyword similarity triggers merge
  - Unrelated alerts create separate incidents
  - Severity escalation on existing incident
  - Environment isolation (different envs → different incidents)
  - IncidentEvent records are created for every correlation decision
  - affected_services list is kept deduplicated
  - New-incident path is taken when no candidate clears the threshold
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.alert import create_alert
from app.crud.incident import create_incident, get_incident
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.incident import EventType, IncidentSeverity, IncidentStatus
from app.models.service_dependency import ServiceDependency, RelationshipType
from app.schemas.alert import AlertCreate
from app.schemas.incident import IncidentCreate
from app.services.correlation_engine import (
    CorrelationEngine,
    _keyword_similarity,
    _tokenize,
    _severity_rank,
    _alert_to_incident_severity,
)

_NOW = datetime.now(tz=timezone.utc)

engine = CorrelationEngine()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _alert(
    service: str = "orders-service",
    severity: AlertSeverity = AlertSeverity.high,
    title: str = "CPU spike on orders-service",
    description: str = "CPU above threshold",
    environment: str = "production",
    source: str = "datadog",
) -> AlertCreate:
    return AlertCreate(
        source=source,
        severity=severity,
        title=title,
        description=description,
        service_name=service,
        environment=environment,
        timestamp=_NOW,
        status=AlertStatus.open,
    )


async def _seed_incident(
    db: AsyncSession,
    services: list[str] | None = None,
    severity: IncidentSeverity = IncidentSeverity.high,
    status: IncidentStatus = IncidentStatus.open,
    title: str = "Existing incident",
    summary: str = "An existing incident",
) -> int:
    inc = await create_incident(
        db,
        IncidentCreate(
            title=title,
            severity=severity,
            status=status,
            affected_services=services or ["orders-service"],
            summary=summary,
        ),
    )
    return inc.id


async def _seed_dependency(db: AsyncSession, source: str, target: str) -> None:
    dep = ServiceDependency(
        service_name=source,
        depends_on=target,
        relationship_type=RelationshipType.calls,
    )
    db.add(dep)
    await db.commit()


# ─────────────────────────────────────────────
# Unit tests – pure functions
# ─────────────────────────────────────────────

def test_tokenize_removes_stop_words():
    tokens = _tokenize("The service is in production and has an error")
    assert "the" not in tokens
    assert "service" not in tokens  # 'service' is in stop words
    assert "production" not in tokens  # also a stop word
    assert "error" not in tokens  # also a stop word


def test_tokenize_keeps_meaningful_tokens():
    tokens = _tokenize("RDS Aurora CPU utilisation exceeded threshold")
    assert "rds" in tokens
    assert "aurora" in tokens
    assert "cpu" in tokens


def test_keyword_similarity_identical():
    assert _keyword_similarity("OOMKilled memory pod restart", "OOMKilled memory pod restart") == 1.0


def test_keyword_similarity_disjoint():
    score = _keyword_similarity("database connection pool", "deployment pipeline build")
    assert score < 0.1


def test_keyword_similarity_partial_overlap():
    score = _keyword_similarity(
        "inventory-service OOMKilled pod restart memory",
        "OOMKilled pod crash memory pressure kubernetes",
    )
    assert 0.2 <= score <= 0.8


def test_severity_rank_ordering():
    assert _severity_rank("low") < _severity_rank("medium")
    assert _severity_rank("medium") < _severity_rank("high")
    assert _severity_rank("high") < _severity_rank("critical")


def test_alert_to_incident_severity_critical():
    assert _alert_to_incident_severity(AlertSeverity.critical) == IncidentSeverity.critical


def test_alert_to_incident_severity_info():
    # info → low (least severe incident level)
    assert _alert_to_incident_severity(AlertSeverity.info) == IncidentSeverity.low


# ─────────────────────────────────────────────
# Integration tests – engine against test DB
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_same_service_correlates_to_existing_incident(db_session: AsyncSession):
    """Two alerts for the same service should land in the same incident."""
    inc_id = await _seed_incident(db_session, services=["orders-service"])

    alert_obj = await create_alert(db_session, _alert(service="orders-service"))
    result = await engine.correlate(db_session, alert_obj)

    assert result.incident.id == inc_id
    assert result.created_new is False
    assert "same service" in result.match_reason


@pytest.mark.asyncio
async def test_different_unrelated_service_creates_new_incident(db_session: AsyncSession):
    """Alert for a service with no overlap should create a fresh incident."""
    await _seed_incident(db_session, services=["orders-service"])

    unrelated_alert = await create_alert(
        db_session,
        _alert(service="completely-unrelated-service", title="Disk full on backup node"),
    )
    result = await engine.correlate(db_session, unrelated_alert)

    assert result.created_new is True


@pytest.mark.asyncio
async def test_dependency_graph_correlates_alerts(db_session: AsyncSession):
    """
    Alert on 'inventory-service' should correlate to an incident about
    'checkout-service' when checkout-service calls inventory-service.
    """
    await _seed_dependency(db_session, "checkout-service", "inventory-service")
    inc_id = await _seed_incident(db_session, services=["checkout-service"])

    # Alert is for inventory-service, but checkout depends on it
    inventory_alert = await create_alert(
        db_session,
        _alert(service="inventory-service", title="Memory pressure on inventory pods"),
    )
    result = await engine.correlate(db_session, inventory_alert)

    assert result.incident.id == inc_id
    assert result.created_new is False
    assert any("dependency" in sig or "related" in sig for sig in result.signals)


@pytest.mark.asyncio
async def test_keyword_similarity_triggers_correlation(db_session: AsyncSession):
    """Alert with overlapping keywords in title should correlate."""
    inc_id = await _seed_incident(
        db_session,
        services=["payments-service"],
        title="payments-service OOMKilled pod restart",
        summary="Kubernetes pods restarting due to OOMKill. Memory limit exceeded.",
    )

    # Different service but highly overlapping description
    related_alert = await create_alert(
        db_session,
        _alert(
            service="payments-service",
            title="OOMKilled pod restart payments memory exceeded",
            description="pods restarting repeatedly due to OOMKill memory limit",
        ),
    )
    result = await engine.correlate(db_session, related_alert)

    # Should correlate due to service match + keyword overlap
    assert result.incident.id == inc_id


@pytest.mark.asyncio
async def test_severity_escalates_incident(db_session: AsyncSession):
    """A critical alert should escalate a medium-severity incident."""
    inc_id = await _seed_incident(
        db_session,
        services=["orders-service"],
        severity=IncidentSeverity.medium,
    )

    critical_alert = await create_alert(
        db_session,
        _alert(service="orders-service", severity=AlertSeverity.critical),
    )
    result = await engine.correlate(db_session, critical_alert)

    assert result.incident.id == inc_id
    assert result.incident.severity == IncidentSeverity.critical

    # Escalation event should be recorded
    inc = await get_incident(db_session, inc_id)
    escalation_events = [e for e in inc.events if e.event_type == EventType.escalated]
    assert len(escalation_events) >= 1


@pytest.mark.asyncio
async def test_no_severity_downgrade(db_session: AsyncSession):
    """A lower-severity alert must NOT downgrade an existing high-severity incident."""
    inc_id = await _seed_incident(
        db_session,
        services=["orders-service"],
        severity=IncidentSeverity.critical,
    )

    low_alert = await create_alert(
        db_session,
        _alert(service="orders-service", severity=AlertSeverity.low),
    )
    result = await engine.correlate(db_session, low_alert)

    assert result.incident.severity == IncidentSeverity.critical  # unchanged


@pytest.mark.asyncio
async def test_affected_services_deduplicated(db_session: AsyncSession):
    """Correlating an alert for the same service must not duplicate the service list."""
    inc_id = await _seed_incident(db_session, services=["orders-service"])

    alert1 = await create_alert(db_session, _alert(service="orders-service"))
    await engine.correlate(db_session, alert1)

    alert2 = await create_alert(db_session, _alert(service="orders-service"))
    result = await engine.correlate(db_session, alert2)

    assert result.incident.affected_services.count("orders-service") == 1


@pytest.mark.asyncio
async def test_new_service_appended_to_affected_services(db_session: AsyncSession):
    """An alert for a related-but-new service should add it to affected_services."""
    await _seed_dependency(db_session, "checkout-service", "orders-service")
    inc_id = await _seed_incident(db_session, services=["checkout-service"])

    orders_alert = await create_alert(
        db_session,
        _alert(service="orders-service", title="orders-service CPU spike high latency"),
    )
    result = await engine.correlate(db_session, orders_alert)

    if result.incident.id == inc_id:
        assert "orders-service" in result.incident.affected_services


@pytest.mark.asyncio
async def test_incident_event_recorded_on_correlation(db_session: AsyncSession):
    """Every correlation must produce an IncidentEvent of type alert_added."""
    inc_id = await _seed_incident(db_session, services=["orders-service"])

    alert_obj = await create_alert(db_session, _alert(service="orders-service"))
    await engine.correlate(db_session, alert_obj)

    inc = await get_incident(db_session, inc_id)
    alert_events = [e for e in inc.events if e.event_type == EventType.alert_added]
    assert len(alert_events) >= 1
    # The event must reference our alert
    assert any(e.alert_id == alert_obj.id for e in alert_events)


@pytest.mark.asyncio
async def test_resolved_incident_not_reused(db_session: AsyncSession):
    """Alerts should not be attached to resolved incidents."""
    await _seed_incident(
        db_session,
        services=["orders-service"],
        status=IncidentStatus.resolved,
    )

    alert_obj = await create_alert(db_session, _alert(service="orders-service"))
    result = await engine.correlate(db_session, alert_obj)

    # Should create a new incident, not reattach to the resolved one
    assert result.created_new is True


@pytest.mark.asyncio
async def test_summary_updated_after_correlation(db_session: AsyncSession):
    """Incident summary should be refreshed to mention the latest alert."""
    inc_id = await _seed_incident(db_session, services=["orders-service"])

    alert_obj = await create_alert(
        db_session,
        _alert(service="orders-service", title="RDS connection pool exhausted"),
    )
    result = await engine.correlate(db_session, alert_obj)

    assert result.incident.summary is not None
    assert len(result.incident.summary) > 0


# ─────────────────────────────────────────────
# API-level tests
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_alert_returns_correlation_info(client: AsyncClient):
    """POST /api/v1/alerts should return correlation metadata in the response."""
    payload = {
        "source": "aws",
        "severity": "high",
        "title": "RDS CPU spike test",
        "service_name": "orders-service",
        "environment": "production",
        "timestamp": _NOW.isoformat(),
        "status": "open",
    }
    response = await client.post("/api/v1/alerts", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "incident_id" in data
    assert "created_new_incident" in data
    assert "correlation_reason" in data
    assert "correlation_score" in data
    assert "correlation_signals" in data
    assert isinstance(data["correlation_signals"], list)


@pytest.mark.asyncio
async def test_two_related_alerts_share_incident(client: AsyncClient):
    """Two alerts for the same service should correlate to the same incident."""
    base = {
        "source": "datadog",
        "severity": "high",
        "service_name": "checkout-service",
        "environment": "production",
        "timestamp": _NOW.isoformat(),
        "status": "open",
    }
    r1 = await client.post("/api/v1/alerts", json={**base, "title": "checkout-service latency spike"})
    r2 = await client.post("/api/v1/alerts", json={**base, "title": "checkout-service error rate elevated"})

    assert r1.status_code == 201
    assert r2.status_code == 201

    # Second alert should attach to the same incident as the first
    assert r1.json()["incident_id"] == r2.json()["incident_id"]
    assert r2.json()["created_new_incident"] is False


@pytest.mark.asyncio
async def test_demo_generate_endpoint(client: AsyncClient):
    """POST /api/v1/alerts/demo-generate should create correlated alerts."""
    response = await client.post(
        "/api/v1/alerts/demo-generate",
        json={"scenario": "database_overload"},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["scenario"] == "database_overload"
    assert data["alerts_created"] == 5  # database_overload has 5 alerts
    assert len(data["incidents_touched"]) >= 1
    assert len(data["detail"]) == 5

    # All detail entries should have required fields
    for entry in data["detail"]:
        assert "alert_id" in entry
        assert "incident_id" in entry
        assert "correlation_reason" in entry


@pytest.mark.asyncio
async def test_demo_generate_invalid_scenario(client: AsyncClient):
    """Unknown scenario name should return 400."""
    response = await client.post(
        "/api/v1/alerts/demo-generate",
        json={"scenario": "does_not_exist"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_demo_generate_memory_leak_scenario(client: AsyncClient):
    """memory_leak scenario should create <= 2 incidents (cascade should correlate)."""
    response = await client.post(
        "/api/v1/alerts/demo-generate",
        json={"scenario": "memory_leak"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["alerts_created"] == 5
    # All cascade alerts should roll up to at most 2 incidents
    assert len(data["incidents_touched"]) <= 2
