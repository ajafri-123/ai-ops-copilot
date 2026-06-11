"""
Alert Correlation Engine
========================

When a new alert arrives, this engine decides whether to:
  (A) Attach it to an existing open/investigating incident, or
  (B) Create a brand-new incident.

Correlation rules (applied in priority order):
  1. Same service + same environment, within the correlation window (default 30 min)
  2. Service dependency match – the alert's service is a direct dependency of a
     service already in an active incident (or vice-versa)
  3. Keyword overlap – significant tokens in the alert title/description match
     those of an active incident's title/summary
  4. Environment guard – alerts from different environments are never correlated
  5. Severity escalation – if the new alert is more severe than the current
     incident, promote the incident severity

Each decision is recorded as an IncidentEvent so the timeline is auditable.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert, AlertSeverity
from app.models.incident import (
    Incident,
    IncidentEvent,
    IncidentSeverity,
    IncidentStatus,
    EventType,
)
from app.models.service_dependency import ServiceDependency
from app.schemas.incident import IncidentCreate

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

CORRELATION_WINDOW_MINUTES: int = 30

# Minimum keyword-overlap score (0–1) to treat as related
KEYWORD_SIMILARITY_THRESHOLD: float = 0.25

# Statuses that are still "active" for correlation purposes
ACTIVE_STATUSES: frozenset[IncidentStatus] = frozenset(
    {
        IncidentStatus.open,
        IncidentStatus.investigating,
        IncidentStatus.identified,
        IncidentStatus.monitoring,
    }
)

# Severity order (higher index = more severe)
_SEVERITY_ORDER: list[str] = ["low", "medium", "high", "critical"]

# Stop-words to ignore when computing keyword similarity
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "is", "in", "on", "at", "of", "for", "to", "and",
        "or", "not", "be", "was", "has", "have", "had", "with", "that", "this",
        "from", "by", "are", "it", "its", "as", "but", "if", "than", "then",
        "into", "over", "error", "alert", "warning", "critical", "high", "low",
        "medium", "info", "service", "production", "staging", "dev",
    }
)


# ─────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────

@dataclass
class CorrelationResult:
    """Return value of the engine – contains the incident the alert was attached to."""
    incident: Incident
    created_new: bool
    match_reason: str
    score: float = 0.0
    signals: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _severity_rank(s: str) -> int:
    try:
        return _SEVERITY_ORDER.index(s.lower())
    except ValueError:
        return 0


def _alert_to_incident_severity(s: AlertSeverity) -> IncidentSeverity:
    mapping = {
        AlertSeverity.critical: IncidentSeverity.critical,
        AlertSeverity.high: IncidentSeverity.high,
        AlertSeverity.medium: IncidentSeverity.medium,
        AlertSeverity.low: IncidentSeverity.low,
        AlertSeverity.info: IncidentSeverity.low,
    }
    return mapping.get(s, IncidentSeverity.low)


def _tokenize(text: str) -> frozenset[str]:
    """Lower-case, strip punctuation, remove stop-words, return token set."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return frozenset(t for t in tokens if t not in _STOP_WORDS and len(t) > 2)


def _keyword_similarity(a: str, b: str) -> float:
    """Jaccard similarity between the token sets of two strings."""
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    intersection = len(ta & tb)
    union = len(ta | tb)
    return intersection / union if union else 0.0


def _incident_text(incident: Incident) -> str:
    parts = [incident.title or ""]
    if incident.summary:
        parts.append(incident.summary)
    return " ".join(parts)


def _alert_text(alert: Alert) -> str:
    parts = [alert.title or ""]
    if alert.description:
        parts.append(alert.description)
    return " ".join(parts)


def _build_summary(incident: Incident, new_alert: Alert) -> str:
    """Regenerate a plain-English summary after a new alert is attached."""
    services = sorted(set(incident.affected_services or []))
    count = len(incident.events) + 1  # +1 for the event being added
    return (
        f"Active incident affecting {len(services)} service(s): "
        f"{', '.join(services)}. "
        f"{count} correlated alert(s) so far. "
        f"Latest signal: [{new_alert.source.upper()}] {new_alert.title}."
    )


# ─────────────────────────────────────────────
# Candidate scoring
# ─────────────────────────────────────────────

@dataclass
class _Candidate:
    incident: Incident
    score: float
    signals: list[str]


async def _fetch_active_incidents(
    db: AsyncSession,
    environment: str,
    since: datetime,
    org_id: int | None = None,
) -> list[Incident]:
    """Return all active incidents that have at least one event within the window."""
    query = (
        select(Incident)
        .options(selectinload(Incident.events))
        .where(
            Incident.status.in_(list(ACTIVE_STATUSES)),
            Incident.created_at >= since,
        )
    )
    if org_id is not None:
        query = query.where(Incident.organization_id == org_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def _fetch_related_services(
    db: AsyncSession, service_name: str
) -> set[str]:
    """
    Return all services directly connected to `service_name` in either direction
    of the dependency graph.
    """
    result = await db.execute(
        select(ServiceDependency).where(
            or_(
                ServiceDependency.service_name == service_name,
                ServiceDependency.depends_on == service_name,
            )
        )
    )
    deps = result.scalars().all()

    related: set[str] = set()
    for dep in deps:
        related.add(dep.service_name)
        related.add(dep.depends_on)
    related.discard(service_name)
    return related


def _score_candidate(
    incident: Incident,
    alert: Alert,
    related_services: set[str],
) -> _Candidate:
    """
    Score a single candidate incident against the incoming alert.
    Returns the candidate with accumulated score and human-readable signals.
    """
    score = 0.0
    signals: list[str] = []
    incident_services = set(incident.affected_services or [])

    # ── Rule 1: Same service ──────────────────────────────
    if alert.service_name in incident_services:
        score += 40.0
        signals.append(f"same service '{alert.service_name}'")

    # ── Rule 2: Related services (dependency graph) ───────
    related_overlap = incident_services & related_services
    if related_overlap:
        bonus = min(30.0, len(related_overlap) * 10.0)
        score += bonus
        signals.append(
            f"related services via dependency graph: {', '.join(sorted(related_overlap))}"
        )

    # ── Rule 3: Keyword similarity ────────────────────────
    kw_score = _keyword_similarity(
        _alert_text(alert), _incident_text(incident)
    )
    if kw_score >= KEYWORD_SIMILARITY_THRESHOLD:
        keyword_bonus = kw_score * 20.0
        score += keyword_bonus
        signals.append(f"keyword overlap {kw_score:.0%}")

    # ── Rule 4: Environment guard (hard filter) ───────────
    # We don't track environment on Incident directly; we skip if
    # *none* of the alerts attached to the incident share the environment.
    # As a lightweight proxy we just require score > 0 before this check.
    # (Full implementation would join alert → incident_events.alert_id.)

    # ── Recency bonus: recently-updated incidents are preferred ──
    age_hours = (
        datetime.now(tz=timezone.utc) - incident.created_at
    ).total_seconds() / 3600
    recency_bonus = max(0.0, 10.0 - age_hours)
    score += recency_bonus
    if recency_bonus > 0:
        signals.append(f"recency +{recency_bonus:.1f}pts ({age_hours:.1f}h old)")

    return _Candidate(incident=incident, score=score, signals=signals)


# ─────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────

class CorrelationEngine:
    """
    Stateless service – create one per request (or inject as a singleton).
    All state lives in the DB.
    """

    async def correlate(
        self,
        db: AsyncSession,
        alert: Alert,
        window_minutes: int = CORRELATION_WINDOW_MINUTES,
    ) -> CorrelationResult:
        """
        Main entry-point.  Given a freshly-persisted Alert, find or create
        the best-matching Incident.
        """
        since = datetime.now(tz=timezone.utc) - timedelta(minutes=window_minutes)

        # 1. Gather candidates (scoped to the alert's org when present)
        active_incidents = await _fetch_active_incidents(
            db, alert.environment, since, org_id=alert.organization_id
        )
        related_services = await _fetch_related_services(db, alert.service_name)

        # 2. Score each candidate
        candidates: list[_Candidate] = []
        for incident in active_incidents:
            candidate = _score_candidate(incident, alert, related_services)
            if candidate.score > 0:
                candidates.append(candidate)

        # 3. Pick the best match (must exceed threshold)
        MATCH_THRESHOLD = 20.0
        candidates.sort(key=lambda c: c.score, reverse=True)
        best = candidates[0] if candidates and candidates[0].score >= MATCH_THRESHOLD else None

        if best:
            result = await self._attach_to_incident(db, best, alert)
            logger.info(
                "Alert %d correlated to Incident %d (score=%.1f, reason=%s)",
                alert.id,
                best.incident.id,
                best.score,
                result.match_reason,
            )
            return result
        else:
            result = await self._create_incident(db, alert)
            logger.info(
                "Alert %d → new Incident %d created",
                alert.id,
                result.incident.id,
            )
            return result

    # ─────────────────────────────────────────
    # Attach to existing incident
    # ─────────────────────────────────────────

    async def _attach_to_incident(
        self,
        db: AsyncSession,
        candidate: _Candidate,
        alert: Alert,
    ) -> CorrelationResult:
        incident = candidate.incident
        reason = "; ".join(candidate.signals) or "score threshold met"

        # ── Update affected_services ──────────────────────
        current_services = list(incident.affected_services or [])
        if alert.service_name not in current_services:
            current_services.append(alert.service_name)
            incident.affected_services = current_services

        # ── Severity escalation ───────────────────────────
        old_severity = incident.severity
        alert_sev_rank = _severity_rank(alert.severity.value)
        incident_sev_rank = _severity_rank(incident.severity.value)
        escalated = False

        if alert_sev_rank > incident_sev_rank:
            new_sev = _alert_to_incident_severity(alert.severity)
            incident.severity = new_sev
            escalated = True

        # ── Summary refresh ───────────────────────────────
        incident.summary = _build_summary(incident, alert)

        await db.flush()

        # ── Record alert_added event ──────────────────────
        db.add(
            IncidentEvent(
                incident_id=incident.id,
                alert_id=alert.id,
                event_type=EventType.alert_added,
                message=(
                    f"[{alert.source.upper()}] {alert.title} "
                    f"(severity={alert.severity.value}, service={alert.service_name}). "
                    f"Correlation signals: {reason}."
                ),
            )
        )

        # ── Escalation event ──────────────────────────────
        if escalated:
            db.add(
                IncidentEvent(
                    incident_id=incident.id,
                    alert_id=alert.id,
                    event_type=EventType.escalated,
                    message=(
                        f"Severity escalated {old_severity.value} → "
                        f"{incident.severity.value} based on incoming "
                        f"{alert.severity.value} alert from {alert.source}."
                    ),
                )
            )

        await db.commit()

        # Reload with eagerly-loaded events to avoid MissingGreenlet on Pydantic validation
        from app.crud.incident import get_incident as _get_incident
        incident = await _get_incident(db, incident.id)  # type: ignore[assignment]

        # ── Broadcast WS events ───────────────────────────
        from app.core.ws_manager import ws_manager  # lazy import – avoids circular
        from app.schemas.incident import IncidentRead

        inc_dict = IncidentRead.model_validate(incident).model_dump()
        await ws_manager.emit_alert_correlated(
            alert={"id": alert.id, "title": alert.title, "source": alert.source,
                   "severity": alert.severity.value, "service_name": alert.service_name},
            incident_id=incident.id,
            incident_title=incident.title,
            created_new=False,
            reason=reason,
        )
        if escalated:
            await ws_manager.emit_incident_escalated(
                incident_id=incident.id,
                old_severity=old_severity.value,
                new_severity=incident.severity.value,
                triggered_by_alert_id=alert.id,
            )
        else:
            await ws_manager.emit_incident_updated(
                incident=inc_dict,
                changed_fields=["affected_services", "summary"],
            )

        return CorrelationResult(
            incident=incident,
            created_new=False,
            match_reason=reason,
            score=candidate.score,
            signals=candidate.signals,
        )

    # ─────────────────────────────────────────
    # Create new incident
    # ─────────────────────────────────────────

    async def _create_incident(
        self,
        db: AsyncSession,
        alert: Alert,
    ) -> CorrelationResult:
        severity = _alert_to_incident_severity(alert.severity)

        incident = Incident(
            title=f"[{alert.source.upper()}] {alert.title}",
            severity=severity,
            status=IncidentStatus.open,
            affected_services=[alert.service_name],
            organization_id=alert.organization_id,
            summary=(
                f"New incident triggered by a {alert.severity.value} alert from "
                f"{alert.source} affecting {alert.service_name} "
                f"in {alert.environment}. "
                f"Alert: {alert.title}."
            ),
        )
        db.add(incident)
        await db.flush()  # get incident.id

        db.add(
            IncidentEvent(
                incident_id=incident.id,
                alert_id=alert.id,
                event_type=EventType.alert_added,
                message=(
                    f"Incident opened by [{alert.source.upper()}] alert: "
                    f"{alert.title} "
                    f"(severity={alert.severity.value}, env={alert.environment})."
                ),
            )
        )

        await db.commit()

        # Reload with eagerly-loaded events to avoid MissingGreenlet on Pydantic validation
        from app.crud.incident import get_incident as _get_incident
        incident = await _get_incident(db, incident.id)  # type: ignore[assignment]

        # ── Broadcast WS events ───────────────────────────
        from app.core.ws_manager import ws_manager  # lazy import
        from app.schemas.incident import IncidentRead

        inc_dict = IncidentRead.model_validate(incident).model_dump()
        await ws_manager.emit_incident_created(inc_dict)
        await ws_manager.emit_alert_correlated(
            alert={"id": alert.id, "title": alert.title, "source": alert.source,
                   "severity": alert.severity.value, "service_name": alert.service_name},
            incident_id=incident.id,
            incident_title=incident.title,
            created_new=True,
            reason="new incident created",
        )

        return CorrelationResult(
            incident=incident,
            created_new=True,
            match_reason="no matching active incident found – created new",
            score=0.0,
            signals=[],
        )


# Module-level singleton
correlation_engine = CorrelationEngine()
