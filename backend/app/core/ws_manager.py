"""
WebSocket Connection Manager
============================
Tracks every active WS connection and fans out structured JSON events
to all connected clients.

Event envelope:
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


class WebSocketManager:
    def __init__(self) -> None:
        # Set of active connections; each is a raw FastAPI WebSocket
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    # ─────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info("WS client connected. Total connections: %d", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)
        logger.info("WS client disconnected. Total connections: %d", len(self._connections))

    # ─────────────────────────────────────────
    # Broadcasting
    # ─────────────────────────────────────────

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        """Send a structured event to every connected client."""
        envelope = {
            "event": event,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "data": data,
        }
        message = json.dumps(envelope, default=str)

        dead: list[WebSocket] = []
        async with self._lock:
            snapshot = list(self._connections)

        for ws in snapshot:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)
            logger.info("Removed %d dead WS connections.", len(dead))

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    # ─────────────────────────────────────────
    # Typed event helpers
    # ─────────────────────────────────────────

    async def emit_alert_created(self, alert: dict[str, Any]) -> None:
        await self.broadcast("alert.created", alert)

    async def emit_alert_correlated(
        self,
        alert: dict[str, Any],
        incident_id: int,
        incident_title: str,
        created_new: bool,
        reason: str,
    ) -> None:
        await self.broadcast(
            "alert.correlated",
            {
                "alert": alert,
                "incident_id": incident_id,
                "incident_title": incident_title,
                "created_new_incident": created_new,
                "reason": reason,
            },
        )

    async def emit_incident_created(self, incident: dict[str, Any]) -> None:
        await self.broadcast("incident.created", incident)

    async def emit_incident_updated(
        self,
        incident: dict[str, Any],
        changed_fields: list[str],
    ) -> None:
        await self.broadcast(
            "incident.updated",
            {"incident": incident, "changed_fields": changed_fields},
        )

    async def emit_incident_escalated(
        self,
        incident_id: int,
        old_severity: str,
        new_severity: str,
        triggered_by_alert_id: int | None = None,
    ) -> None:
        await self.broadcast(
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
