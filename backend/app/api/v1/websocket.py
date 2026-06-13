"""
WebSocket endpoint  –  ws://host/api/v1/ws

Clients connect here and receive a continuous stream of JSON events.
On connect the server immediately sends:
  1. A "connection.ack" event with server metadata
  2. A "snapshot" event carrying the last 20 open alerts and 10 active incidents
     scoped to the authenticated org.

Authentication is REQUIRED: pass the JWT as the `token` query parameter:
  ws://host/api/v1/ws?token=<jwt>

Connections with a missing, invalid, or expired token are rejected with
close code 4401 before any data is sent.
"""

import json
import logging
from datetime import datetime, timezone

import jwt as pyjwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.core.ws_manager import ws_manager
from app.crud.alert import list_alerts
from app.models.alert import AlertStatus
from app.models.incident import Incident, IncidentStatus
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

WS_CLOSE_UNAUTHORIZED = 4401


async def _send(ws: WebSocket, event: str, data: dict) -> None:
    """Send a structured event to a single client, handling datetime serialisation."""
    envelope = {
        "event": event,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "data": data,
    }
    await ws.send_text(json.dumps(envelope, default=str))


def _extract_org_id(token: str | None) -> int | None:
    """Return org_id from a JWT, or None if absent / invalid / expired."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        org_id = payload.get("org_id")
        return int(org_id) if org_id is not None else None
    except (pyjwt.InvalidTokenError, TypeError, ValueError):
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    token: str | None = Query(default=None, description="JWT bearer token (required)"),
) -> None:
    org_id = _extract_org_id(token)
    if org_id is None:
        # Must accept before close so the client receives the close code.
        await ws.accept()
        await ws.close(code=WS_CLOSE_UNAUTHORIZED, reason="Authentication required")
        return

    await ws_manager.connect(ws, org_id)
    try:
        # ── Send initial snapshot (strictly org-scoped) ───────
        async with AsyncSessionLocal() as db:
            _, recent_alerts = await list_alerts(
                db,
                org_id=org_id,
                skip=0,
                limit=20,
                status=AlertStatus.open,
            )

            inc_query = (
                select(Incident)
                .options(selectinload(Incident.events))
                .where(
                    Incident.organization_id == org_id,
                    Incident.status.in_(
                        [IncidentStatus.open, IncidentStatus.investigating,
                         IncidentStatus.identified, IncidentStatus.monitoring]
                    ),
                )
                .order_by(Incident.created_at.desc())
                .limit(10)
            )

            inc_result = await db.execute(inc_query)
            active_incidents = inc_result.scalars().all()

        from app.schemas.alert import AlertRead
        from app.schemas.incident import IncidentRead

        await _send(ws, "connection.ack", {
            "message": "Connected to AI Ops Copilot real-time feed",
            "authenticated": True,
        })

        await _send(ws, "snapshot", {
            "alerts": [AlertRead.model_validate(a).model_dump(mode="json") for a in recent_alerts],
            "incidents": [IncidentRead.model_validate(i).model_dump(mode="json") for i in active_incidents],
        })

        # ── Keep connection alive, wait for client disconnect ─
        while True:
            try:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
            except Exception:
                break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected cleanly.")
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        await ws_manager.disconnect(ws, org_id)
