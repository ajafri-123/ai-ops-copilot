"""
AI Service Layer
================
Provider pattern with two implementations:

  OpenAIProvider  – calls GPT-4o / GPT-4o-mini with JSON mode
  MockProvider    – deterministic pattern-matching fallback (no API key needed)

The facade `AIService.analyze()` picks the right provider at call time,
so the rest of the codebase never needs to know which one is active.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.schemas.analysis import RCAResult, TimelineEntry

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Context object handed to every provider
# ─────────────────────────────────────────────────────────────────────────────

class IncidentContext:
    """
    Everything a provider needs to know about the incident, pre-serialised
    so providers don't need to touch SQLAlchemy objects.
    """

    def __init__(
        self,
        incident_id: int,
        title: str,
        severity: str,
        status: str,
        affected_services: list[str],
        existing_summary: str | None,
        alerts: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> None:
        self.incident_id = incident_id
        self.title = title
        self.severity = severity
        self.status = status
        self.affected_services = affected_services
        self.existing_summary = existing_summary
        self.alerts = alerts          # list of alert dicts (source, severity, title, etc.)
        self.events = events          # list of incident event dicts

    def as_prompt_text(self) -> str:
        """Render context as a structured plain-text block for the LLM."""
        lines: list[str] = [
            f"INCIDENT #{self.incident_id}",
            f"Title    : {self.title}",
            f"Severity : {self.severity.upper()}",
            f"Status   : {self.status}",
            f"Services : {', '.join(self.affected_services) or 'unknown'}",
            "",
        ]

        if self.existing_summary:
            lines += ["CURRENT SUMMARY:", self.existing_summary, ""]

        if self.alerts:
            lines.append("CORRELATED ALERTS (chronological):")
            for a in sorted(self.alerts, key=lambda x: x.get("timestamp", "")):
                ts = a.get("timestamp", "?")[:19]
                lines.append(
                    f"  [{ts}] [{a.get('source','?').upper()}] "
                    f"[{a.get('severity','?').upper()}] "
                    f"{a.get('service_name','?')} – "
                    f"{a.get('title','?')}"
                )
                if a.get("description"):
                    lines.append(f"         {a['description'][:200]}")
            lines.append("")

        if self.events:
            lines.append("INCIDENT EVENT TIMELINE:")
            for e in sorted(self.events, key=lambda x: x.get("timestamp", "")):
                ts = e.get("timestamp", "?")[:19]
                lines.append(
                    f"  [{ts}] [{e.get('event_type','?')}] {e.get('message','?')}"
                )

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Abstract provider
# ─────────────────────────────────────────────────────────────────────────────

class AnalysisProvider(ABC):
    @abstractmethod
    async def analyze(self, ctx: IncidentContext) -> RCAResult:
        ...


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI provider
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert Site Reliability Engineer (SRE) and incident response assistant \
embedded in an AI Operations Copilot platform.

Your job is to analyze infrastructure incidents given a set of correlated alerts \
and an event timeline. You must reason like a seasoned on-call engineer who has \
seen hundreds of production incidents.

Always respond with a single JSON object that matches this exact schema:

{
  "summary": "<2–4 sentence executive summary for non-technical stakeholders>",
  "root_cause": "<technical root-cause narrative, 2–6 sentences, cite specific alerts>",
  "timeline": [
    {
      "timestamp": "<ISO-8601 or HH:MM relative>",
      "event": "<what happened>",
      "source": "<which system>",
      "significance": "low|medium|high|critical"
    }
  ],
  "remediation_steps": [
    "<step 1: immediate action>",
    "<step 2: stabilisation>",
    "..."
  ],
  "confidence": <0.0–1.0 float, your confidence in this analysis>,
  "risk_level": "low|medium|high|critical"
}

Rules:
- Root cause must be specific and technical. Vague answers like "something went wrong" are not acceptable.
- Timeline must be chronologically ordered, include only real events from the provided data.
- Remediation steps must be concrete shell commands, k8s commands, or specific actions.
  Do NOT list vague advice like "monitor the system".
- confidence: 0.9+ only if you have clear causal evidence; 0.5–0.8 for likely causes; <0.5 if speculative.
- risk_level reflects the current blast radius to end users.
- Respond with JSON only. No markdown, no explanation outside the JSON object.
"""


class OpenAIProvider(AnalysisProvider):
    def __init__(self) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    async def analyze(self, ctx: IncidentContext) -> RCAResult:
        user_content = (
            "Analyze the following incident and produce the JSON response described "
            "in your instructions.\n\n"
            + ctx.as_prompt_text()
        )

        logger.info(
            "Sending incident #%d to OpenAI (%s) — %d alerts, %d events",
            ctx.incident_id,
            self._model,
            len(ctx.alerts),
            len(ctx.events),
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            temperature=0.2,   # low temp for factual analysis
            max_tokens=2048,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )

        raw = response.choices[0].message.content or "{}"
        data: dict = json.loads(raw)

        # Parse timeline entries
        timeline = [
            TimelineEntry(**t)
            for t in data.get("timeline", [])
            if isinstance(t, dict)
        ]

        return RCAResult(
            summary=data.get("summary", ""),
            root_cause=data.get("root_cause", ""),
            timeline=timeline,
            remediation_steps=data.get("remediation_steps", []),
            confidence=float(data.get("confidence", 0.5)),
            risk_level=data.get("risk_level", "medium"),
            provider="openai",
            model=self._model,
            analyzed_at=datetime.now(tz=timezone.utc),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Mock provider — intelligent, pattern-based, works with zero API key
# ─────────────────────────────────────────────────────────────────────────────

# Pattern rules: (regex against concatenated alert titles) → analysis template
_MOCK_PATTERNS: list[tuple[str, dict]] = [
    (
        r"oom|memory|heap|out.of.memory|crash.loop",
        {
            "root_cause_template": (
                "A memory leak or unbounded allocation in {primary_service} caused "
                "the container to exceed its memory limit, triggering repeated OOMKill events. "
                "As the pod entered CrashLoopBackOff, in-flight requests were dropped, "
                "propagating latency and errors to all services that call {primary_service}. "
                "The cascading timeouts exhausted upstream connection pools and produced "
                "the observed spike in HTTP 5xx responses."
            ),
            "summary_template": (
                "A memory leak in {primary_service} caused cascading failures across "
                "{service_count} services. {alert_count} alerts were correlated over "
                "{duration}. User-facing error rate peaked during the CrashLoopBackOff window."
            ),
            "remediation": [
                "kubectl set resources deployment/{primary_service} --limits=memory=1Gi -n production",
                "kubectl rollout restart deployment/{primary_service} -n production",
                "kubectl rollout status deployment/{primary_service} -n production --timeout=120s",
                "Monitor p99 latency on downstream services — expect recovery within 5 minutes.",
                "Review heap profile: kubectl exec -it <pod> -- curl localhost:8080/debug/pprof/heap",
                "File a post-incident ticket to add memory profiling to the CI pipeline.",
            ],
            "confidence": 0.87,
            "risk_level": "critical",
        },
    ),
    (
        r"cpu|throttl|high.load|utilis",
        {
            "root_cause_template": (
                "CPU utilisation on {primary_service} saturated available compute capacity, "
                "causing request queuing and p99 latency to exceed acceptable thresholds. "
                "Root cause is likely an inefficient query pattern (N+1 queries or missing index) "
                "introduced in a recent deployment, combined with elevated production traffic. "
                "The resulting connection pool exhaustion propagated timeouts to dependent services."
            ),
            "summary_template": (
                "CPU saturation on {primary_service} degraded {service_count} services over {duration}. "
                "{alert_count} correlated alerts point to a query-performance regression "
                "as the origin. Immediate action should focus on query optimisation and "
                "horizontal scaling."
            ),
            "remediation": [
                "kubectl scale deployment/{primary_service} --replicas=8 -n production",
                "Run EXPLAIN ANALYZE on the top slow queries from pg_stat_statements.",
                "Check for missing indexes: SELECT * FROM pg_stat_user_tables WHERE idx_scan < 100;",
                "Temporarily increase DB connection pool size in application config.",
                "Review the last 3 deployments with git log --oneline -n 20 for N+1 query changes.",
                "Add a DB query time alert at 500ms threshold to catch regressions earlier.",
            ],
            "confidence": 0.81,
            "risk_level": "high",
        },
    ),
    (
        r"deploy|rollout|release|version|rollback",
        {
            "root_cause_template": (
                "A faulty deployment introduced a breaking change to {primary_service}. "
                "The defect — likely a configuration mismatch, missing environment variable, "
                "or schema incompatibility — manifested immediately after the rollout completed. "
                "The automated rollback policy should revert traffic to the last stable version; "
                "however, any in-flight state mutations (DB writes, queue messages) during the "
                "bad deployment window will need manual review."
            ),
            "summary_template": (
                "A bad deployment of {primary_service} caused {service_count} services to degrade "
                "over {duration}. {alert_count} alerts were correlated. "
                "Rollback to the previous version is the fastest mitigation path."
            ),
            "remediation": [
                "kubectl rollout undo deployment/{primary_service} -n production",
                "kubectl rollout status deployment/{primary_service} -n production --timeout=120s",
                "Verify error rate drops below 1%: watch -n5 'curl -s localhost/metrics | grep http_errors'",
                "Inspect the diff: git diff HEAD~1 HEAD -- config/ .env* charts/",
                "If rollback insufficient, pin the last known-good image tag explicitly.",
                "Block the broken version from re-deploying until root cause is confirmed.",
            ],
            "confidence": 0.84,
            "risk_level": "high",
        },
    ),
    (
        r"queue|dlq|dead.letter|backlog|consumer|lag",
        {
            "root_cause_template": (
                "Message consumer throughput for {primary_service} dropped significantly, "
                "causing queue depth to grow beyond acceptable limits. The degradation is "
                "likely caused by either a schema mismatch in message payloads (causing "
                "deserialization errors and DLQ routing) or consumer thread saturation from "
                "a spike in message volume. Messages in the DLQ represent real business "
                "transactions that require manual reprocessing."
            ),
            "summary_template": (
                "Consumer lag on {primary_service} accumulated {alert_count} correlated alerts "
                "over {duration}. Messages in the dead-letter queue represent failed transactions "
                "requiring recovery. Immediate focus should be on fixing the consumer and "
                "replaying the DLQ."
            ),
            "remediation": [
                "Identify failed message schema: aws sqs receive-message --queue-url <dlq-url> --max-number-of-messages 1",
                "Deploy consumer hotfix to handle the new payload schema.",
                "After deploy, replay DLQ: aws lambda invoke --function-name dlq-redrive --payload '{}'",
                "Scale consumers: kubectl scale deployment/{primary_service} --replicas=6 -n production",
                "Monitor queue depth until it reaches zero: watch -n10 'aws sqs get-queue-attributes --queue-url <url>'",
                "Add DLQ depth alert at threshold 10 to catch this earlier next time.",
            ],
            "confidence": 0.79,
            "risk_level": "medium",
        },
    ),
    (
        r"network|partition|connectivity|latency|timeout|az|availab",
        {
            "root_cause_template": (
                "A network-layer disruption impacted connectivity between {primary_service} "
                "and its dependencies. The pattern of simultaneous failures across multiple "
                "services in the same availability zone is consistent with either a VPC routing "
                "change, a security group misconfiguration, or an underlying AWS AZ-level event. "
                "The database failover event confirms the primary was unreachable for a period, "
                "which would have caused transaction timeouts for all writers."
            ),
            "summary_template": (
                "A network disruption affecting {service_count} services was detected "
                "over {duration}. {alert_count} alerts from AWS, Kubernetes, and Datadog "
                "corroborate an infrastructure-level event. Recovery requires verifying "
                "network connectivity and confirming DB failover completed successfully."
            ),
            "remediation": [
                "Verify AZ health in AWS Console → EC2 → Service Health Dashboard.",
                "Check VPC routing tables: aws ec2 describe-route-tables --filters Name=tag:Env,Values=production",
                "Confirm DB failover: aws rds describe-db-clusters --db-cluster-identifier prod-aurora",
                "Test inter-service connectivity: kubectl exec -it <pod> -- curl -I http://orders-service/health",
                "Review security group rules for recent changes: aws ec2 describe-security-group-rules",
                "Enable VPC Flow Logs if not already on to capture future events.",
            ],
            "confidence": 0.75,
            "risk_level": "critical",
        },
    ),
]

_DEFAULT_MOCK = {
    "root_cause_template": (
        "{primary_service} is experiencing degraded performance that is impacting "
        "{service_count} dependent services. The correlated alerts across "
        "{alert_count} monitoring sources indicate a systemic issue rather than "
        "an isolated component failure. Further investigation is needed to identify "
        "the precise root cause; the timeline below provides the available evidence."
    ),
    "summary_template": (
        "An operational incident is affecting {primary_service} and {service_count} "
        "related services. {alert_count} alerts were correlated over {duration}. "
        "The AI analysis has identified probable contributing factors; review the "
        "timeline and remediation steps."
    ),
    "remediation": [
        "Check service health: kubectl get pods -n production | grep -v Running",
        "Review recent deployments: kubectl rollout history deployment/{primary_service} -n production",
        "Inspect application logs: kubectl logs -l app={primary_service} --tail=200 -n production",
        "Verify external dependencies are healthy.",
        "Escalate to the owning team if not resolved within 15 minutes.",
    ],
    "confidence": 0.55,
    "risk_level": "high",
}


def _duration_str(alerts: list[dict]) -> str:
    """Calculate human-readable span between first and last alert."""
    timestamps = []
    for a in alerts:
        ts_str = a.get("timestamp")
        if ts_str:
            try:
                timestamps.append(datetime.fromisoformat(ts_str.replace("Z", "+00:00")))
            except ValueError:
                pass
    if len(timestamps) < 2:
        return "a short window"
    span = abs((max(timestamps) - min(timestamps)).total_seconds())
    if span < 120:
        return f"{int(span)}s"
    if span < 3600:
        return f"{int(span/60)} minutes"
    return f"{span/3600:.1f} hours"


class MockProvider(AnalysisProvider):
    """
    Deterministic mock that produces plausible-looking analysis by pattern-matching
    against alert titles. No API key required. Always fast.
    """

    async def analyze(self, ctx: IncidentContext) -> RCAResult:
        logger.info(
            "Using MockProvider for incident #%d (no OPENAI_API_KEY configured)",
            ctx.incident_id,
        )

        # ── Pick template via pattern matching ──────────────────
        all_text = " ".join(
            (a.get("title", "") + " " + (a.get("description") or "")).lower()
            for a in ctx.alerts
        ) + " " + ctx.title.lower()

        template = _DEFAULT_MOCK
        for pattern, tmpl in _MOCK_PATTERNS:
            if re.search(pattern, all_text):
                template = tmpl
                break

        # ── Resolve template variables ──────────────────────────
        primary_service = (
            ctx.affected_services[0] if ctx.affected_services else "the affected service"
        )
        service_count = len(ctx.affected_services)
        alert_count = len(ctx.alerts)
        duration = _duration_str(ctx.alerts)

        def fmt(s: str) -> str:
            return s.format(
                primary_service=primary_service,
                service_count=service_count,
                alert_count=alert_count,
                duration=duration,
            )

        # ── Build timeline from events + alerts ─────────────────
        timeline: list[TimelineEntry] = []
        seen: set[str] = set()

        # Add alerts to timeline
        for a in sorted(ctx.alerts, key=lambda x: x.get("timestamp", "")):
            sev = a.get("severity", "medium")
            ts = a.get("timestamp", "")[:16]
            msg = f"[{a.get('source','?').upper()}] {a.get('service_name','?')}: {a.get('title','?')}"
            if msg not in seen:
                seen.add(msg)
                timeline.append(
                    TimelineEntry(
                        timestamp=ts,
                        event=msg,
                        source=a.get("source", "unknown"),
                        significance=sev if sev in {"low","medium","high","critical"} else "medium",
                    )
                )

        # Add notable incident events (non-alert_added) to timeline
        for e in sorted(ctx.events, key=lambda x: x.get("timestamp", "")):
            if e.get("event_type") in {"alert_added"}:
                continue
            ts = e.get("timestamp", "")[:16]
            msg = e.get("message", "")[:120]
            if msg and msg not in seen:
                seen.add(msg)
                timeline.append(
                    TimelineEntry(
                        timestamp=ts,
                        event=msg,
                        source="system",
                        significance="medium",
                    )
                )

        # ── Adjust confidence based on data richness ────────────
        base_confidence: float = template["confidence"]  # type: ignore[assignment]
        confidence = min(
            0.95,
            base_confidence
            + 0.03 * min(alert_count, 5)   # more alerts → more confidence
            + (0.05 if service_count > 2 else 0.0),
        )

        remediation = [fmt(step) for step in template["remediation"]]  # type: ignore[index]

        return RCAResult(
            summary=fmt(template["summary_template"]),  # type: ignore[index]
            root_cause=fmt(template["root_cause_template"]),  # type: ignore[index]
            timeline=timeline,
            remediation_steps=remediation,
            confidence=round(confidence, 2),
            risk_level=template["risk_level"],  # type: ignore[index]
            provider="mock",
            model="pattern-matching-v1",
            analyzed_at=datetime.now(tz=timezone.utc),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Facade
# ─────────────────────────────────────────────────────────────────────────────

class AIService:
    """
    Pick the right provider at call time.
    If OPENAI_API_KEY is set and non-empty → OpenAIProvider (singleton).
    Otherwise → MockProvider (singleton).
    """

    def __init__(self) -> None:
        self._openai_provider: OpenAIProvider | None = None
        self._mock_provider: MockProvider = MockProvider()

    def _get_provider(self) -> AnalysisProvider:
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
            if self._openai_provider is None:
                self._openai_provider = OpenAIProvider()
            return self._openai_provider
        return self._mock_provider

    async def analyze_incident(self, ctx: IncidentContext) -> RCAResult:
        provider = self._get_provider()
        try:
            return await provider.analyze(ctx)
        except Exception as exc:
            logger.error(
                "Primary AI provider failed (%s), falling back to mock: %s",
                type(provider).__name__,
                exc,
            )
            return await self._mock_provider.analyze(ctx)

    # Legacy stub kept for backward compatibility
    async def root_cause_analysis(self, incident_description: str) -> RCAResult:
        ctx = IncidentContext(
            incident_id=0,
            title=incident_description,
            severity="unknown",
            status="open",
            affected_services=[],
            existing_summary=None,
            alerts=[],
            events=[],
        )
        return await self.analyze_incident(ctx)

    async def summarize_alerts(self, alerts: list[dict]) -> str:
        return f"Received {len(alerts)} alert(s). Use /analyze for full AI analysis."


ai_service = AIService()
