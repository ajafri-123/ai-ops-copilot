from fastapi import APIRouter

from app.api.v1 import auth, health, alerts, incidents, integrations, websocket, analysis, graph

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(health.router)
router.include_router(alerts.router)
router.include_router(incidents.router)
router.include_router(integrations.router)
router.include_router(analysis.router)
router.include_router(graph.router)
router.include_router(websocket.router)
