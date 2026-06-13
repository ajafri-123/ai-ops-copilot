"""
Service-dependency graph endpoint.
GET /api/v1/incidents/{id}/graph

Returns a nodes-and-edges payload that the frontend React Flow graph
can consume directly. Nodes are the incident's affected services plus
their first-degree neighbours from service_dependencies. Edges carry
relationship type and are coloured by whether the endpoint service is
affected by the incident.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import AuthContext, get_auth
from app.crud.incident import get_incident
from app.models.service_dependency import ServiceDependency

router = APIRouter(tags=["Graph"])


# ── Response models ──────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    affected: bool          # is this service part of the incident?
    group: str              # "primary" | "dependency"


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str       # depends_on | calls | reads_from | etc.


class ServiceGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get(
    "/incidents/{incident_id}/graph",
    response_model=ServiceGraphResponse,
    summary="Service dependency graph for an incident",
)
async def get_incident_graph(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(get_auth),
) -> ServiceGraphResponse:
    incident = await get_incident(db, incident_id)
    if not incident or incident.organization_id != ctx.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {incident_id} not found",
        )

    affected: set[str] = set(incident.affected_services or [])
    if not affected:
        return ServiceGraphResponse(nodes=[], edges=[])

    # Fetch this org's dependency rows where either end touches an affected
    # service — topology must never leak across tenants.
    result = await db.execute(
        select(ServiceDependency).where(
            ServiceDependency.organization_id == ctx.org_id,
            or_(
                ServiceDependency.service_name.in_(list(affected)),
                ServiceDependency.depends_on.in_(list(affected)),
            ),
        )
    )
    deps = result.scalars().all()

    # Build node set
    node_ids: dict[str, str] = {}   # id → group
    for svc in affected:
        node_ids[svc] = "primary"
    for dep in deps:
        if dep.service_name not in node_ids:
            node_ids[dep.service_name] = "dependency"
        if dep.depends_on not in node_ids:
            node_ids[dep.depends_on] = "dependency"

    nodes = [
        GraphNode(
            id=svc,
            label=svc,
            affected=svc in affected,
            group=group,
        )
        for svc, group in node_ids.items()
    ]

    edges = [
        GraphEdge(
            id=f"{dep.service_name}-{dep.depends_on}-{dep.relationship_type}",
            source=dep.service_name,
            target=dep.depends_on,
            relationship=dep.relationship_type,
        )
        for dep in deps
    ]

    return ServiceGraphResponse(nodes=nodes, edges=edges)
