"""
Pydantic schemas for AI root-cause analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    timestamp: str = Field(..., description="ISO-8601 or human-readable time")
    event: str = Field(..., description="What happened at this moment")
    source: str = Field(..., description="Which system reported this")
    significance: Literal["low", "medium", "high", "critical"] = "medium"


class RCAResult(BaseModel):
    """Full structured output from the AI analysis engine."""

    summary: str = Field(..., description="2–4 sentence executive summary")
    root_cause: str = Field(..., description="Technical root cause narrative")
    timeline: list[TimelineEntry] = Field(
        default_factory=list,
        description="Chronological reconstruction of events",
    )
    remediation_steps: list[str] = Field(
        default_factory=list,
        description="Ordered list of actionable remediation steps",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Model confidence 0–1",
    )
    risk_level: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Current risk to the system / users",
    )
    # Extra metadata
    provider: str = Field(default="mock", description="Which provider produced this")
    model: str = Field(default="mock", description="Model identifier")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class AnalyzeResponse(BaseModel):
    """HTTP response from POST /incidents/{id}/analyze"""

    incident_id: int
    analysis: RCAResult
    alerts_analyzed: int
    events_analyzed: int
