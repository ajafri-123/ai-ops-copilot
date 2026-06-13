"""
WebSocket Connection Manager
============================
Tracks active WS connections *per organization* and fans out structured
JSON events only to clients belonging to that org.

Events are published through Redis pub/sub so that emitters running in
other processes (Celery workers, additional API replicas) still reach
every connected dashboard: every emit publishes to the `ws:events`
channel, and each API process runs a relay task (see `start_relay`) that
subscribes and delivers messages to its local connections.

Event envelope (as delivered to clients):
  {
    "event":     "<event_type>",        # e.g. "alert.created"
    "timestamp": "<iso-8601>",
    "data":      { ... }                # event-specific payload
  }

Event types:
  alert.created         – a new alert was ingested
  alert.correlated      – alert was attached to an existing incident
  incident.created      – a brand-new incident was opened
  incident.updated      – severity / status / services changed
  incident.escalated    – severity was bumped up
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

REDIS_CHANNEL = "ws:events"


class WebSocketManager:
    def __init__(self) -> None:
        # org_id → set of active connections for that org
        self._connections: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._relay_task: asyncio.Task | None = None

    # ─────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────

    async def connect(self, ws: WebSocket, org_id: int) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(org_id, set()).add(ws)
        logger.info(
            "WS client connected (org=%d). Total connections: %d",
            org_id, self.connection_count,
        )

    async def disconnect(self, ws: WebSocket, org_id: int) -> None:
        async with self._lock:
            conns = self._connections.get(org_id)
            if conns is not None:
                conns.discard(ws)
                if not conns:
                    self._connections.pop(org_id, None)
        logger.info(
            "WS client disconnected (org=%d). Total connections: %d",
            org_id, self.connection_count,
        )

    # ─────────────────────────────────────────
    # Redis relay – run one per API process
    # ─────────────────────────────────────────

    def start_relay(self) -> None:
        """Start the background task that relays Redis pub/sub events to local clients."""
        if self._relay_task is None or self._relay_task.done():
            self._relay_task = asyncio.create_task(self._relay_loop())

    async def stop_relay(self) -> None:
        if self._relay_task is not None:
            self._relay_task.cancel()
            try:
                await self._relay_task
            except asyncio.CancelledError:
                pass
            self._relay_task = None

    async def _relay_loop(self) -> None:
        from app.core.redis import get_redis

        while True:
            try:
                pubsub = get_redis().pubsub()
                await pubsub.subscribe(REDIS_CHANNEL)
                logger.info("WS relay subscribed to Redis channel %r", REDIS_CHANNEL)
                async for msg in pubsub.listen():
                    if msg.get("type") != "message":
                        continue
                    try:
                        payload = json.loads(msg["data"])
                        org_id = payload.pop("org_id", None)
                        if org_id is None:
                            continue
                        await self._send_local(int(org_id), json.dumps(payload, default=str))
                    except Exception:
                        logger.exception("WS relay failed to process message")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("WS relay connection lost (%s); retrying in 2s", exc)
                await asyncio.sleep(2)

    # ─────────────────────────────────────────
    # Broadcasting
    # ─────────────────────────────────────────

    async def broadcast(self, org_id: int | None, event: str, data: dict[str, Any]) -> None:
        """
        Publish a structured event for one organization.

        Goes through Redis pub/sub so every API process (and only clients of
        `org_id`) receives it, regardless of which process or worker emitted it.
        Falls back to local-only delivery if Redis is unavailable.
        """
        if org_id is None:
            # No tenant context → never broadcast (prevents cross-tenant leaks).
            logger.warning("Dropping WS event %r with no org_id", event)
            return

        envelope = {
            "event": event,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "data": data,
        }

        try:
            from app.core.redis import get_redis
            await get_redis().publish(
                REDIS_CHANNEL, json.dumps({**envelope, "org_id": org_id}, default=str)
            )
        except Exception as exc:
            logger.warning("Redis publish failed (%s); falling back to local broadcast", exc)
            await self._send_local(org_id, json.dumps(envelope, default=str))

    async def _send_local(self, org_id: int, message: str) -> None:
        """Send a serialized envelope to this process's connections for one org."""
        async with self._lock:
            snapshot = list(self._connections.get(org_id, ()))

        dead: list[WebSocket] = []
        for ws in snapshot:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                conns = self._connections.get(org_id)
                if conns is not None:
                    for ws in dead:
                        conns.discard(ws)
                    if not conns:
                        self._connections.pop(org_id, None)
            logger.info("Removed %d dead WS connections (org=%d).", len(dead), org_id)

    @property
    def connection_count(self) -> int:
        return sum(len(c) for c in self._connections.values())

    # ─────────────────────────────────────────
    # Typed event helpers
    # ─────────────────────────────────────────

    async def emit_alert_created(self, org_id: int | None, alert: dict[str, Any]) -> None:
        await self.broadcast(org_id, "alert.created", alert)

    async def emit_alert_correlated(
        self,
        org_id: int | None,
        alert: dict[str, Any],
        incident_id: int,
        incident_title: str,
        created_new: bool,
        reason: str,
    ) -> None:
        await self.broadcast(
            org_id,
            "alert.correlated",
            {
                "alert": alert,
                "incident_id": incident_id,
                "incident_title": incident_title,
                "created_new_incident": created_new,
                "reason": reason,
            },
        )

    async def emit_incident_created(self, org_id: int | None, incident: dict[str, Any]) -> None:
        await self.broadcast(org_id, "incident.created", incident)

    async def emit_incident_updated(
        self,
        org_id: int | None,
        incident: dict[str, Any],
        changed_fields: list[str],
    ) -> None:
        await self.broadcast(
            org_id,
            "incident.updated",
            {"incident": incident, "changed_fields": changed_fields},
        )

    async def emit_incident_escalated(
        self,
        org_id: int | None,
        incident_id: int,
        old_severity: str,
        new_severity: str,
        triggered_by_alert_id: int | None = None,
    ) -> None:
        await self.broadcast(
            org_id,
            "incident.escalated",
            {
                "incident_id": incident_id,
                "old_severity": old_severity,
                "new_severity": new_severity,
                "triggered_by_alert_id": triggered_by_alert_id,
            },
        )


# Module-level singleton shared across the app
ws_manager = WebSocketManager()
