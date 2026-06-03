"""
Celery task definitions for AI Ops Copilot.

All tasks follow the same pattern:
  1. Accept plain-Python arguments (IDs, strings) — no SQLAlchemy objects
  2. Build their own async DB session via AsyncSessionLocal
  3. Execute async business logic using asyncio.run()
  4. Log clearly with [task_name] prefix so grep is easy
  5. Return a plain dict so the result backend can serialise it

Task inventory:
  process_alert        – full pipeline: save → correlate → optionally analyse
  correlate_alert      – correlation only (used when alert is already saved)
  analyze_incident_bg  – AI root-cause analysis in the low-priority queue
  generate_demo_alerts – periodic: fire a random demo scenario
  worker_heartbeat     – periodic: lightweight liveness probe
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

from celery import Task
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app
from app.core.config import settings

logger = get_task_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(coro):
    """Run an async coroutine synchronously inside a Celery task."""
    return asyncio.run(coro)


# ─────────────────────────────────────────────────────────────────────────────
# Task 1 — process_alert
# Full pipeline: given an already-persisted alert_id, run correlation and
# (optionally) queue AI analysis for the resulting incident.
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="tasks.process_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def process_alert(self: Task, alert_id: int) -> dict:
    """
    Run the correlation engine for a saved alert, then optionally enqueue
    AI analysis if AUTO_ANALYZE_NEW_INCIDENTS is enabled.

    Args:
        alert_id: PK of the Alert row that was just created.
    """
    logger.info("[process_alert] starting alert_id=%d task=%s", alert_id, self.request.id)

    async def _run_pipeline(alert_id: int) -> dict:
        from app.core.database import AsyncSessionLocal
        from app.crud.alert import get_alert
        from app.services.correlation_engine import correlation_engine
        from app.core.ws_manager import ws_manager
        from app.schemas.alert import AlertRead

        async with AsyncSessionLocal() as db:
            alert = await get_alert(db, alert_id)
            if alert is None:
                logger.warning("[process_alert] alert_id=%d not found, skipping", alert_id)
                return {"status": "skipped", "reason": "alert not found", "alert_id": alert_id}

            logger.info(
                "[process_alert] correlating alert_id=%d source=%s service=%s severity=%s",
                alert_id, alert.source, alert.service_name, alert.severity.value,
            )

            # Broadcast alert.created so dashboard reflects it immediately
            await ws_manager.emit_alert_created(
                AlertRead.model_validate(alert).model_dump()
            )

            # Run correlation engine
            result = await correlation_engine.correlate(db, alert)

            logger.info(
                "[process_alert] alert_id=%d → incident_id=%d new=%s score=%.1f",
                alert_id, result.incident.id, result.created_new, result.score,
            )

            incident_id = result.incident.id

        # Optionally trigger AI analysis in the analysis queue
        if settings.AUTO_ANALYZE_NEW_INCIDENTS and result.created_new:
            analyze_incident_bg.apply_async(args=[incident_id], queue="analysis")
            logger.info(
                "[process_alert] queued AI analysis for new incident_id=%d", incident_id
            )

        return {
            "status": "ok",
            "alert_id": alert_id,
            "incident_id": incident_id,
            "created_new_incident": result.created_new,
            "correlation_score": round(result.score, 2),
        }

    try:
        return _run(_run_pipeline(alert_id))
    except Exception as exc:
        logger.error("[process_alert] alert_id=%d failed: %s", alert_id, exc, exc_info=True)
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# Task 2 — correlate_alert
# Lighter task: just run the correlation engine (no WS broadcast, no AI).
# Useful for bulk ingestion where the API already handled the broadcast.
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="tasks.correlate_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def correlate_alert(self: Task, alert_id: int) -> dict:
    """
    Run only the correlation engine for an alert.
    Assumes the alert was already persisted and broadcast by the API.
    """
    logger.info("[correlate_alert] alert_id=%d task=%s", alert_id, self.request.id)

    async def _correlate(alert_id: int) -> dict:
        from app.core.database import AsyncSessionLocal
        from app.crud.alert import get_alert
        from app.services.correlation_engine import correlation_engine

        async with AsyncSessionLocal() as db:
            alert = await get_alert(db, alert_id)
            if alert is None:
                return {"status": "skipped", "reason": "alert not found"}

            result = await correlation_engine.correlate(db, alert)
            logger.info(
                "[correlate_alert] alert_id=%d → incident_id=%d score=%.1f",
                alert_id, result.incident.id, result.score,
            )
            return {
                "status": "ok",
                "alert_id": alert_id,
                "incident_id": result.incident.id,
                "created_new_incident": result.created_new,
                "match_reason": result.match_reason,
            }

    try:
        return _run(_correlate(alert_id))
    except Exception as exc:
        logger.error("[correlate_alert] alert_id=%d failed: %s", alert_id, exc, exc_info=True)
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# Task 3 — analyze_incident_bg
# Low-priority queue.  Runs the AI analysis pipeline and broadcasts the result.
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    name="tasks.analyze_incident_bg",
    bind=True,
    max_retries=2,
    default_retry_delay=30,     # wait 30 s before retry (OpenAI rate limits)
    acks_late=True,
    soft_time_limit=90,         # graceful cancel after 90 s
    time_limit=120,             # hard kill after 120 s
)
def analyze_incident_bg(self: Task, incident_id: int) -> dict:
    """
    Run AI root-cause analysis for an incident in the background.
    Results are persisted to the DB and broadcast via WebSocket.

    Args:
        incident_id: PK of the Incident row to analyse.
    """
    logger.info("[analyze_incident_bg] incident_id=%d task=%s", incident_id, self.request.id)

    async def _analyze(incident_id: int) -> dict:
        from app.core.database import AsyncSessionLocal
        from app.services.analysis_pipeline import run_analysis_pipeline

        async with AsyncSessionLocal() as db:
            response = await run_analysis_pipeline(incident_id, db)
            return {
                "status": "ok",
                "incident_id": incident_id,
                "provider": response.analysis.provider,
                "model": response.analysis.model,
                "confidence": response.analysis.confidence,
                "risk_level": response.analysis.risk_level,
                "alerts_analyzed": response.alerts_analyzed,
            }

    try:
        result = _run(_analyze(incident_id))
        logger.info(
            "[analyze_incident_bg] done incident_id=%d provider=%s confidence=%.2f",
            incident_id,
            result.get("provider", "?"),
            result.get("confidence", 0),
        )
        return result
    except ValueError as exc:
        # Incident not found — don't retry
        logger.warning("[analyze_incident_bg] incident_id=%d not found: %s", incident_id, exc)
        return {"status": "skipped", "reason": str(exc), "incident_id": incident_id}
    except Exception as exc:
        logger.error(
            "[analyze_incident_bg] incident_id=%d failed: %s", incident_id, exc, exc_info=True
        )
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# Task 4 — generate_demo_alerts  (periodic, Beat-scheduled)
# Picks a random scenario and fires alerts through the full pipeline.
# Only active when DEMO_PERIODIC_ALERTS=true.
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="tasks.generate_demo_alerts")
def generate_demo_alerts() -> dict:
    """
    Periodic task: pick a random demo scenario, create alerts, run correlation.
    Each alert fires process_alert as a sub-task so the WS broadcast and
    correlation happen correctly even when many alerts arrive at once.
    """
    if not settings.DEMO_PERIODIC_ALERTS:
        logger.debug("[generate_demo_alerts] DEMO_PERIODIC_ALERTS=false, skipping")
        return {"status": "disabled"}

    from app.services.demo_generator import AVAILABLE_SCENARIOS, build_alerts_for_scenario

    scenario = random.choice(AVAILABLE_SCENARIOS)
    logger.info("[generate_demo_alerts] firing scenario=%s", scenario)

    async def _create_alerts(scenario: str) -> list[int]:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.core.seed import DEMO_ORG_SLUG
        from app.crud.alert import create_alert
        from app.models.organization import Organization
        from app.schemas.alert import AlertCreate

        alert_dicts = build_alerts_for_scenario(scenario)
        alert_ids: list[int] = []

        async with AsyncSessionLocal() as db:
            # Scope demo alerts to the demo org so they appear on the dashboard
            demo_org = (
                await db.execute(
                    select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
                )
            ).scalar_one_or_none()
            demo_org_id: int | None = demo_org.id if demo_org else None

            for data in alert_dicts:
                alert = await create_alert(db, AlertCreate(**data), org_id=demo_org_id)
                alert_ids.append(alert.id)
                logger.info(
                    "[generate_demo_alerts] created alert_id=%d service=%s severity=%s org_id=%s",
                    alert.id, alert.service_name, alert.severity.value, demo_org_id,
                )

        return alert_ids

    try:
        alert_ids = _run(_create_alerts(scenario))
    except Exception as exc:
        logger.error("[generate_demo_alerts] failed to create alerts: %s", exc, exc_info=True)
        return {"status": "error", "reason": str(exc)}

    # Enqueue a process_alert task for each alert (stagger by 2 s to avoid DB contention)
    for i, aid in enumerate(alert_ids):
        process_alert.apply_async(
            args=[aid],
            queue="alerts",
            countdown=i * 2,     # stagger: 0s, 2s, 4s, 6s, 8s
        )

    logger.info(
        "[generate_demo_alerts] scenario=%s alerts=%d tasks enqueued",
        scenario, len(alert_ids),
    )
    return {
        "status": "ok",
        "scenario": scenario,
        "alerts_created": len(alert_ids),
        "alert_ids": alert_ids,
        "fired_at": datetime.now(tz=timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Task 5 — worker_heartbeat  (periodic, Beat-scheduled every 30 s)
# Lightweight liveness probe.  Just logs and returns uptime info.
# ─────────────────────────────────────────────────────────────────────────────

@celery_app.task(name="tasks.worker_heartbeat")
def worker_heartbeat() -> dict:
    """Periodic heartbeat — confirms the worker and Beat are alive."""
    now = datetime.now(tz=timezone.utc).isoformat()
    logger.debug("[worker_heartbeat] alive at %s", now)
    return {"status": "alive", "timestamp": now}
