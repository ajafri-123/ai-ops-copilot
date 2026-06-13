"""
Seed the database with realistic demo data.

Run once at startup (if tables are empty) so the dashboard has something to show
immediately after `docker compose up`.

Sources represented:
  • AWS CloudWatch
  • Datadog
  • Sentry
  • GitHub Actions
  • Kubernetes
"""

import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.integration import Integration, IntegrationProvider, IntegrationStatus
from app.models.incident import (
    Incident,
    IncidentEvent,
    IncidentSeverity,
    IncidentStatus,
    EventType,
)
from app.models.membership import Membership, MemberRole
from app.models.organization import Organization
from app.models.service_dependency import ServiceDependency, RelationshipType
from app.models.user import User

logger = logging.getLogger(__name__)

_NOW = datetime.now(tz=timezone.utc)


def _ago(minutes: int = 0, hours: int = 0) -> datetime:
    return _NOW - timedelta(minutes=minutes, hours=hours)


# ─────────────────────────────────────────────────────────────
# Raw alert fixtures
# ─────────────────────────────────────────────────────────────

ALERT_FIXTURES: list[dict] = [
    # ── AWS CloudWatch ──────────────────────────────────────
    {
        "source": "aws",
        "severity": AlertSeverity.critical,
        "title": "RDS CPU Utilisation > 95% for 10 minutes",
        "description": (
            "The Aurora PostgreSQL cluster aiops-prod-db is running at 97% CPU. "
            "Slow query log shows N+1 query patterns from the orders-service."
        ),
        "service_name": "orders-db",
        "environment": "production",
        "timestamp": _ago(minutes=42),
        "status": AlertStatus.open,
        "raw_payload": {
            "AlarmName": "RDS-HighCPU-aiops-prod-db",
            "AWSAccountId": "123456789012",
            "Region": "us-east-1",
            "NewStateValue": "ALARM",
            "Trigger": {
                "MetricName": "CPUUtilization",
                "Namespace": "AWS/RDS",
                "Threshold": 95.0,
                "EvaluationPeriods": 2,
            },
        },
    },
    {
        "source": "aws",
        "severity": AlertSeverity.high,
        "title": "ALB 5xx Error Rate > 5% on api-gateway",
        "description": (
            "Application Load Balancer reporting 8.3% HTTP 5xx over last 5 minutes. "
            "Target group health checks show 3 of 6 instances unhealthy."
        ),
        "service_name": "api-gateway",
        "environment": "production",
        "timestamp": _ago(minutes=38),
        "status": AlertStatus.open,
        "raw_payload": {
            "AlarmName": "ALB-5xxRate-api-gateway",
            "Region": "us-east-1",
            "Trigger": {
                "MetricName": "HTTPCode_ELB_5XX_Count",
                "Namespace": "AWS/ApplicationELB",
            },
        },
    },
    {
        "source": "aws",
        "severity": AlertSeverity.medium,
        "title": "SQS Dead-Letter Queue depth > 100 messages",
        "description": (
            "payments-dlq has accumulated 187 messages in the last 30 minutes. "
            "Consumer is failing to process payment confirmation events."
        ),
        "service_name": "payments-service",
        "environment": "production",
        "timestamp": _ago(minutes=55),
        "status": AlertStatus.acknowledged,
        "raw_payload": {
            "AlarmName": "SQS-DLQ-Depth-payments-dlq",
            "Region": "us-east-1",
            "Trigger": {"MetricName": "ApproximateNumberOfMessagesNotVisible"},
        },
    },
    {
        "source": "aws",
        "severity": AlertSeverity.low,
        "title": "S3 Bucket versioning disabled on aiops-assets-prod",
        "description": "AWS Config rule s3-bucket-versioning-enabled triggered.",
        "service_name": "asset-storage",
        "environment": "production",
        "timestamp": _ago(hours=2),
        "status": AlertStatus.resolved,
        "raw_payload": {"configRuleName": "s3-bucket-versioning-enabled"},
    },
    # ── Datadog ─────────────────────────────────────────────
    {
        "source": "datadog",
        "severity": AlertSeverity.critical,
        "title": "p99 Latency spike: checkout-service > 8 000 ms",
        "description": (
            "checkout-service p99 response time has exceeded 8 seconds for 5 consecutive minutes. "
            "Trace analysis points to downstream call to inventory-service timing out."
        ),
        "service_name": "checkout-service",
        "environment": "production",
        "timestamp": _ago(minutes=40),
        "status": AlertStatus.open,
        "raw_payload": {
            "monitor_id": 4821903,
            "monitor_name": "checkout-service p99 latency",
            "tags": ["env:production", "service:checkout-service"],
            "query": "avg(last_5m):p99:trace.http.request{service:checkout-service} > 8000",
        },
    },
    {
        "source": "datadog",
        "severity": AlertSeverity.high,
        "title": "Error rate elevated: inventory-service 12% errors",
        "description": (
            "inventory-service is returning errors on 12.4% of requests. "
            "Errors concentrated in GET /v2/products endpoint."
        ),
        "service_name": "inventory-service",
        "environment": "production",
        "timestamp": _ago(minutes=45),
        "status": AlertStatus.open,
        "raw_payload": {
            "monitor_id": 4821704,
            "monitor_name": "inventory-service error rate",
            "tags": ["env:production", "service:inventory-service"],
        },
    },
    {
        "source": "datadog",
        "severity": AlertSeverity.medium,
        "title": "Redis cache hit ratio dropped below 60%",
        "description": (
            "session-cache Redis cluster hit ratio is 54%, down from 89% baseline. "
            "Possible cache eviction storm due to memory pressure."
        ),
        "service_name": "session-cache",
        "environment": "production",
        "timestamp": _ago(hours=1, minutes=10),
        "status": AlertStatus.acknowledged,
        "raw_payload": {
            "monitor_id": 4820011,
            "monitor_name": "Redis cache hit ratio",
        },
    },
    {
        "source": "datadog",
        "severity": AlertSeverity.info,
        "title": "Deployment detected: user-service v2.14.3 → v2.15.0",
        "description": "Datadog deployment tracking recorded a new version rollout.",
        "service_name": "user-service",
        "environment": "production",
        "timestamp": _ago(hours=3),
        "status": AlertStatus.resolved,
        "raw_payload": {
            "event_type": "deploy",
            "service": "user-service",
            "version": "v2.15.0",
        },
    },
    # ── Sentry ──────────────────────────────────────────────
    {
        "source": "sentry",
        "severity": AlertSeverity.critical,
        "title": "UnhandledPromiseRejection: Cannot read properties of null (reading 'price')",
        "description": (
            "TypeError in checkout-service/src/cart/CartService.ts:142. "
            "Affecting 1 200 users in the last 15 minutes. "
            "Likely caused by null product returned from inventory-service during the latency spike."
        ),
        "service_name": "checkout-service",
        "environment": "production",
        "timestamp": _ago(minutes=37),
        "status": AlertStatus.open,
        "raw_payload": {
            "project": "checkout-service",
            "issue_id": "CHECKOUT-4F2A",
            "culprit": "checkout-service/src/cart/CartService.ts in processCart",
            "level": "fatal",
            "times_seen": 1247,
            "first_seen": _ago(minutes=37).isoformat(),
        },
    },
    {
        "source": "sentry",
        "severity": AlertSeverity.high,
        "title": "DatabaseConnectionError: max_connections exceeded on orders-db",
        "description": (
            "psycopg2.OperationalError raised in orders-service. "
            "Connection pool exhausted – matches RDS CPU spike."
        ),
        "service_name": "orders-service",
        "environment": "production",
        "timestamp": _ago(minutes=41),
        "status": AlertStatus.open,
        "raw_payload": {
            "project": "orders-service",
            "issue_id": "ORDERS-7C1B",
            "level": "error",
            "times_seen": 892,
        },
    },
    {
        "source": "sentry",
        "severity": AlertSeverity.medium,
        "title": "PaymentWebhookParseError: unexpected field 'metadata.v2'",
        "description": "Stripe webhook payload schema mismatch in payments-service.",
        "service_name": "payments-service",
        "environment": "production",
        "timestamp": _ago(hours=1),
        "status": AlertStatus.acknowledged,
        "raw_payload": {
            "project": "payments-service",
            "issue_id": "PAYMENTS-9D44",
            "level": "warning",
            "times_seen": 187,
        },
    },
    # ── GitHub Actions ───────────────────────────────────────
    {
        "source": "github_actions",
        "severity": AlertSeverity.high,
        "title": "CI Pipeline failure: orders-service main branch",
        "description": (
            "Workflow 'Deploy to Production' failed at step 'Run integration tests'. "
            "18 tests failed, mostly around DB connection pool limits."
        ),
        "service_name": "orders-service",
        "environment": "ci",
        "timestamp": _ago(minutes=35),
        "status": AlertStatus.open,
        "raw_payload": {
            "workflow": "Deploy to Production",
            "run_id": 11234567890,
            "conclusion": "failure",
            "repository": "acme-corp/orders-service",
            "branch": "main",
            "commit_sha": "a3f1e2d",
            "actor": "deploy-bot",
        },
    },
    {
        "source": "github_actions",
        "severity": AlertSeverity.medium,
        "title": "Security scan: 3 HIGH CVEs found in inventory-service",
        "description": (
            "Trivy container scan found CVE-2024-21626 (runc), "
            "CVE-2024-23653 (BuildKit), CVE-2024-24557 (Moby) in base image."
        ),
        "service_name": "inventory-service",
        "environment": "ci",
        "timestamp": _ago(hours=4),
        "status": AlertStatus.acknowledged,
        "raw_payload": {
            "workflow": "Security Scan",
            "run_id": 11230001234,
            "tool": "trivy",
            "critical_count": 0,
            "high_count": 3,
        },
    },
    # ── Kubernetes ───────────────────────────────────────────
    {
        "source": "kubernetes",
        "severity": AlertSeverity.critical,
        "title": "OOMKilled: inventory-service pod restarted 8 times in 20 minutes",
        "description": (
            "Pod inventory-service-7d9f8b-xvk2p in namespace production "
            "has been OOMKilled repeatedly. Memory limit 512Mi is insufficient. "
            "This correlates with the inventory-service error rate spike."
        ),
        "service_name": "inventory-service",
        "environment": "production",
        "timestamp": _ago(minutes=43),
        "status": AlertStatus.open,
        "raw_payload": {
            "namespace": "production",
            "pod": "inventory-service-7d9f8b-xvk2p",
            "container": "inventory-service",
            "reason": "OOMKilled",
            "restart_count": 8,
            "memory_limit": "512Mi",
            "node": "ip-10-0-1-42.ec2.internal",
        },
    },
    {
        "source": "kubernetes",
        "severity": AlertSeverity.high,
        "title": "HorizontalPodAutoscaler unable to scale checkout-service",
        "description": (
            "HPA checkout-service-hpa is stuck at maxReplicas=10. "
            "CPU target 70% is exceeded (current 94%) but no new nodes available."
        ),
        "service_name": "checkout-service",
        "environment": "production",
        "timestamp": _ago(minutes=39),
        "status": AlertStatus.open,
        "raw_payload": {
            "namespace": "production",
            "hpa": "checkout-service-hpa",
            "current_replicas": 10,
            "desired_replicas": 14,
            "max_replicas": 10,
            "current_cpu": "94%",
        },
    },
    {
        "source": "kubernetes",
        "severity": AlertSeverity.medium,
        "title": "PersistentVolumeClaim Pending: orders-service-pvc-1",
        "description": "PVC orders-service-pvc-1 stuck in Pending state for 12 minutes. No storage available in zone us-east-1a.",
        "service_name": "orders-service",
        "environment": "production",
        "timestamp": _ago(minutes=60),
        "status": AlertStatus.acknowledged,
        "raw_payload": {
            "namespace": "production",
            "pvc": "orders-service-pvc-1",
            "storage_class": "gp3-encrypted",
            "requested": "20Gi",
        },
    },
    {
        "source": "kubernetes",
        "severity": AlertSeverity.low,
        "title": "Node ip-10-0-2-88 disk pressure warning",
        "description": "Node condition DiskPressure=True. /var/lib/docker filesystem at 89%.",
        "service_name": "k8s-node",
        "environment": "production",
        "timestamp": _ago(hours=5),
        "status": AlertStatus.resolved,
        "raw_payload": {
            "node": "ip-10-0-2-88.ec2.internal",
            "condition": "DiskPressure",
            "disk_used_pct": 89,
        },
    },
]


# ─────────────────────────────────────────────────────────────
# Incident fixtures
# ─────────────────────────────────────────────────────────────

INCIDENT_FIXTURES: list[dict] = [
    {
        "title": "Checkout & Inventory Cascade Failure – Production",
        "severity": IncidentSeverity.critical,
        "status": IncidentStatus.investigating,
        "affected_services": [
            "checkout-service",
            "inventory-service",
            "orders-service",
            "orders-db",
            "api-gateway",
        ],
        "summary": (
            "A memory leak in inventory-service caused repeated OOMKill events, "
            "degrading its response time. checkout-service began timing out on "
            "inventory calls, triggering a null-pointer exception in cart processing. "
            "This in turn caused N+1 DB queries in orders-service, exhausting the "
            "Aurora connection pool and spiking RDS CPU to 97%. The ALB is returning "
            "8.3% 5xx errors to end users."
        ),
        "root_cause": (
            "Root cause: inventory-service v3.8.1 introduced an unbounded in-memory "
            "product cache that was never evicted. Under production load the container "
            "exceeded its 512Mi memory limit. OOMKill events caused request queuing "
            "which propagated latency to all dependent services."
        ),
        "remediation_steps": [
            "1. Increase inventory-service memory limit from 512Mi → 1Gi immediately (kubectl apply).",
            "2. Roll back inventory-service to v3.8.0 to remove the unbounded cache.",
            "3. Restart orders-service pods to clear stale DB connection pool state.",
            "4. Monitor RDS CPU – expect recovery within 5 minutes of orders-service restart.",
            "5. Drain and re-process payments DLQ once downstream services stabilise.",
            "6. Post-incident: add memory leak detection to CI pipeline (step 6 in runbook).",
        ],
        "events": [
            {
                "event_type": EventType.alert_added,
                "message": "OOMKilled alert received for inventory-service (8 restarts)",
                "offset_minutes": 43,
            },
            {
                "event_type": EventType.alert_added,
                "message": "Datadog: inventory-service error rate 12% detected",
                "offset_minutes": 45,
            },
            {
                "event_type": EventType.alert_added,
                "message": "Datadog: checkout-service p99 latency > 8 000 ms",
                "offset_minutes": 40,
            },
            {
                "event_type": EventType.alert_added,
                "message": "Sentry: UnhandledPromiseRejection in CartService affecting 1 200 users",
                "offset_minutes": 37,
            },
            {
                "event_type": EventType.alert_added,
                "message": "AWS: RDS CPU 97% – Aurora connection pool nearing limit",
                "offset_minutes": 42,
            },
            {
                "event_type": EventType.status_changed,
                "message": "Incident status changed: open → investigating",
                "offset_minutes": 35,
            },
            {
                "event_type": EventType.ai_analysis,
                "message": "AI Copilot completed root-cause analysis. Memory leak in inventory-service v3.8.1 identified as cascade origin.",
                "offset_minutes": 30,
            },
            {
                "event_type": EventType.comment,
                "message": "On-call engineer @sarah confirmed: kubectl describe pod shows OOMKilled exit code 137.",
                "offset_minutes": 28,
            },
        ],
    },
    {
        "title": "Payments Dead-Letter Queue Backlog",
        "severity": IncidentSeverity.medium,
        "status": IncidentStatus.identified,
        "affected_services": ["payments-service"],
        "summary": (
            "A Stripe webhook schema change introduced an unexpected field 'metadata.v2' "
            "causing the payments-service consumer to throw a parse error and "
            "send messages to the DLQ. 187 payment confirmation events are pending."
        ),
        "root_cause": (
            "Stripe silently added metadata.v2 to webhook payloads on 2026-05-31. "
            "The payments-service schema validator uses strict mode and rejected all payloads."
        ),
        "remediation_steps": [
            "1. Deploy hotfix to switch Pydantic validator to non-strict mode for metadata field.",
            "2. After deploy, replay DLQ messages via AWS Lambda redriving script.",
            "3. Verify all 187 messages are processed successfully in CloudWatch.",
            "4. Add integration test for Stripe webhook forward-compatibility.",
        ],
        "events": [
            {
                "event_type": EventType.alert_added,
                "message": "AWS SQS: DLQ depth 187 messages on payments-dlq",
                "offset_minutes": 55,
            },
            {
                "event_type": EventType.alert_added,
                "message": "Sentry: PaymentWebhookParseError – unexpected field metadata.v2",
                "offset_minutes": 60,
            },
            {
                "event_type": EventType.ai_analysis,
                "message": "AI Copilot correlated DLQ backlog with Sentry parse error. Stripe schema change identified.",
                "offset_minutes": 50,
            },
            {
                "event_type": EventType.status_changed,
                "message": "Status changed: open → identified",
                "offset_minutes": 48,
            },
        ],
    },
    {
        "title": "Orders Service CI Pipeline Blocked",
        "severity": IncidentSeverity.high,
        "status": IncidentStatus.monitoring,
        "affected_services": ["orders-service"],
        "summary": (
            "GitHub Actions deploy pipeline for orders-service is failing due to "
            "integration test failures. Tests are connecting to a shared staging DB "
            "that is also under load from the production incident."
        ),
        "root_cause": (
            "Integration tests share the staging Aurora cluster with production read replicas. "
            "Elevated production load caused staging queries to time out."
        ),
        "remediation_steps": [
            "1. Temporarily disable production read replica routing to staging.",
            "2. Re-run the failed pipeline run.",
            "3. Long term: provision isolated test database for CI.",
        ],
        "events": [
            {
                "event_type": EventType.alert_added,
                "message": "GitHub Actions: Deploy to Production workflow failed on main",
                "offset_minutes": 35,
            },
            {
                "event_type": EventType.status_changed,
                "message": "Status changed: open → monitoring",
                "offset_minutes": 20,
            },
        ],
    },
]


# ─────────────────────────────────────────────────────────────
# Service dependency graph
# ─────────────────────────────────────────────────────────────

SERVICE_DEPENDENCY_FIXTURES: list[dict] = [
    # API gateway is the entry point for all user traffic
    {"service_name": "api-gateway", "depends_on": "checkout-service", "relationship_type": RelationshipType.calls},
    {"service_name": "api-gateway", "depends_on": "orders-service", "relationship_type": RelationshipType.calls},
    {"service_name": "api-gateway", "depends_on": "user-service", "relationship_type": RelationshipType.calls},
    {"service_name": "api-gateway", "depends_on": "inventory-service", "relationship_type": RelationshipType.calls},
    # Checkout depends on inventory and orders
    {"service_name": "checkout-service", "depends_on": "inventory-service", "relationship_type": RelationshipType.calls},
    {"service_name": "checkout-service", "depends_on": "orders-service", "relationship_type": RelationshipType.calls},
    {"service_name": "checkout-service", "depends_on": "payments-service", "relationship_type": RelationshipType.calls},
    {"service_name": "checkout-service", "depends_on": "session-cache", "relationship_type": RelationshipType.reads_from},
    # Orders writes to DB and publishes events
    {"service_name": "orders-service", "depends_on": "orders-db", "relationship_type": RelationshipType.writes_to},
    {"service_name": "orders-service", "depends_on": "orders-db", "relationship_type": RelationshipType.reads_from},
    {"service_name": "orders-service", "depends_on": "payments-service", "relationship_type": RelationshipType.publishes_to},
    # Inventory reads from its own DB
    {"service_name": "inventory-service", "depends_on": "orders-db", "relationship_type": RelationshipType.reads_from},
    # Payments subscribes to orders
    {"service_name": "payments-service", "depends_on": "orders-service", "relationship_type": RelationshipType.subscribes_to},
    # User service uses session cache
    {"service_name": "user-service", "depends_on": "session-cache", "relationship_type": RelationshipType.reads_from},
    {"service_name": "user-service", "depends_on": "session-cache", "relationship_type": RelationshipType.writes_to},
]


# ─────────────────────────────────────────────────────────────
# Seeder entry-point
# ─────────────────────────────────────────────────────────────

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo1234"
DEMO_ORG_NAME = "Demo Organization"
DEMO_ORG_SLUG = "demo"


async def seed_database() -> None:
    """Seed the DB with demo data. Safe to call multiple times – skips if data exists."""
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(Alert).limit(1))).scalar_one_or_none()
        if existing:
            logger.info("Database already seeded – skipping.")
            return

        logger.info("Seeding database with demo data …")

        # ── Demo org + user ──────────────────────────────────
        org = Organization(name=DEMO_ORG_NAME, slug=DEMO_ORG_SLUG)
        db.add(org)
        await db.flush()

        demo_user = User(
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Demo User",
        )
        db.add(demo_user)
        await db.flush()

        db.add(Membership(user_id=demo_user.id, org_id=org.id, role=MemberRole.owner))
        await db.flush()

        # ── Integrations ────────────────────────────────────
        from app.crud.integration import PROVIDER_DEFAULT_CONFIGS, PROVIDER_NAMES
        integration_fixtures = [
            (IntegrationProvider.aws_cloudwatch, IntegrationStatus.connected),
            (IntegrationProvider.datadog, IntegrationStatus.connected),
            (IntegrationProvider.sentry, IntegrationStatus.connected),
            (IntegrationProvider.github_actions, IntegrationStatus.connected),
            (IntegrationProvider.kubernetes, IntegrationStatus.disconnected),
            (IntegrationProvider.slack, IntegrationStatus.disconnected),
        ]
        for provider, intg_status in integration_fixtures:
            config = PROVIDER_DEFAULT_CONFIGS.get(provider) if intg_status == IntegrationStatus.connected else None
            last_sync = _ago(minutes=random.randint(5, 120)) if intg_status == IntegrationStatus.connected else None
            db.add(Integration(
                organization_id=org.id,
                provider=provider,
                name=PROVIDER_NAMES[provider],
                status=intg_status,
                last_sync=last_sync,
                config=config,
            ))
        await db.flush()

        # ── Alerts ──────────────────────────────────────────
        for a in ALERT_FIXTURES:
            db.add(Alert(**a, organization_id=org.id))
        await db.flush()

        # ── Service dependencies (scoped to the demo org) ────
        for dep in SERVICE_DEPENDENCY_FIXTURES:
            db.add(ServiceDependency(**dep, organization_id=org.id))

        # ── Incidents + events ───────────────────────────────
        for inc_data in INCIDENT_FIXTURES:
            events_data = inc_data.pop("events", [])
            incident = Incident(**inc_data, organization_id=org.id, environment="production")
            db.add(incident)
            await db.flush()

            for ev in events_data:
                offset = ev.pop("offset_minutes", 0)
                db.add(IncidentEvent(
                    incident_id=incident.id,
                    timestamp=_ago(minutes=offset),
                    **ev,
                ))

        await db.commit()
        logger.info("Seeding complete. Demo login → email=%s", DEMO_EMAIL)
