"""
Demo Alert Generator
====================
Produces realistic, time-coherent alert sequences that exercise the
correlation engine.  Each scenario is a narrative: a root-cause alert
fires first, followed by cascading signals from dependent services.

Scenarios available:
  database_overload   – RDS CPU spike → connection exhaustion → app errors
  memory_leak         – k8s OOMKill → latency → client errors
  deployment_failure  – bad deploy → elevated error rate → customer impact
  network_partition   – AZ connectivity loss → service unavailability
  queue_backlog       – consumer lag → downstream timeout → DLQ accumulation
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from app.models.alert import AlertSeverity, AlertStatus

_NOW = datetime.now(tz=timezone.utc)


def _ts(offset_minutes: float = 0) -> str:
    """ISO-8601 timestamp offset from now."""
    return (_NOW - timedelta(minutes=offset_minutes)).isoformat()


# ──────────────────────────────────────────────────────────────────────────────
# Scenario definitions
# Each entry in a scenario list is a dict matching AlertCreate fields.
# offset_minutes: how many minutes *before* now the alert fired.
# ──────────────────────────────────────────────────────────────────────────────

SCENARIOS: dict[str, list[dict[str, Any]]] = {

    "database_overload": [
        {
            "source": "aws",
            "severity": AlertSeverity.critical,
            "title": "RDS Aurora CPU Utilisation > 95% sustained",
            "description": (
                "Aurora PostgreSQL cluster prod-aurora-cluster CPU has been above 95% "
                "for 10+ minutes. Slow query log shows full table scans on orders table."
            ),
            "service_name": "orders-db",
            "environment": "production",
            "offset_minutes": 18,
            "raw_payload": {
                "AlarmName": "RDS-HighCPU-prod-aurora",
                "Region": "us-east-1",
                "Trigger": {"MetricName": "CPUUtilization", "Threshold": 95},
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "orders-service DB connection pool exhausted (pool_size=20)",
            "description": (
                "All 20 connections in the orders-service pool are in use. "
                "New requests are queuing. p95 DB query time: 12 400 ms."
            ),
            "service_name": "orders-service",
            "environment": "production",
            "offset_minutes": 14,
            "raw_payload": {
                "monitor_id": 50011,
                "query": "max(last_2m):max:postgresql.connections{service:orders-service} > 20",
            },
        },
        {
            "source": "sentry",
            "severity": AlertSeverity.critical,
            "title": "OperationalError: FATAL: remaining connection slots are reserved",
            "description": (
                "psycopg2.OperationalError raised 743 times in the last 5 minutes "
                "in orders-service/app/db/session.py. "
                "Users cannot complete purchases."
            ),
            "service_name": "orders-service",
            "environment": "production",
            "offset_minutes": 10,
            "raw_payload": {
                "issue_id": "ORDERS-DB-CONN-01",
                "level": "fatal",
                "times_seen": 743,
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "checkout-service HTTP 503 rate > 10% (upstream orders-service unavailable)",
            "description": (
                "10.8% of checkout requests returning 503. "
                "Traces show orders-service call timing out after 30 s."
            ),
            "service_name": "checkout-service",
            "environment": "production",
            "offset_minutes": 8,
            "raw_payload": {
                "monitor_id": 50012,
                "tags": ["env:production", "service:checkout-service"],
            },
        },
        {
            "source": "aws",
            "severity": AlertSeverity.medium,
            "title": "ALB TargetResponseTime p99 > 15 s on checkout target group",
            "description": "Application Load Balancer reporting extreme p99 latency on checkout.",
            "service_name": "api-gateway",
            "environment": "production",
            "offset_minutes": 6,
            "raw_payload": {"AlarmName": "ALB-Latency-checkout-tg"},
        },
    ],

    "memory_leak": [
        {
            "source": "kubernetes",
            "severity": AlertSeverity.high,
            "title": "OOMKilled: inventory-service pod restarted 3 times in 15 minutes",
            "description": (
                "Pod inventory-service-6c8d4b-pqrst OOMKilled. "
                "Memory limit 512Mi. Heap profiler shows unbounded product cache growth."
            ),
            "service_name": "inventory-service",
            "environment": "production",
            "offset_minutes": 22,
            "raw_payload": {
                "namespace": "production",
                "pod": "inventory-service-6c8d4b-pqrst",
                "reason": "OOMKilled",
                "restart_count": 3,
                "memory_limit": "512Mi",
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "inventory-service p99 latency > 5 000 ms",
            "description": (
                "Latency spike coinciding with pod restart thrash. "
                "GC pauses evident in JVM metrics."
            ),
            "service_name": "inventory-service",
            "environment": "production",
            "offset_minutes": 19,
            "raw_payload": {"monitor_id": 60021, "threshold_ms": 5000},
        },
        {
            "source": "sentry",
            "severity": AlertSeverity.critical,
            "title": "NullPointerException: product.price is null in CartService",
            "description": (
                "TypeError in checkout-service CartService:88. "
                "inventory-service returning partial responses during restart window. "
                "1 540 users affected in 10 minutes."
            ),
            "service_name": "checkout-service",
            "environment": "production",
            "offset_minutes": 16,
            "raw_payload": {
                "issue_id": "CART-NPE-02",
                "level": "fatal",
                "times_seen": 1540,
            },
        },
        {
            "source": "kubernetes",
            "severity": AlertSeverity.critical,
            "title": "OOMKilled: inventory-service pod restarted 8 times – CrashLoopBackOff",
            "description": (
                "inventory-service is now in CrashLoopBackOff. "
                "Back-off delay 5 minutes. Service effectively unavailable."
            ),
            "service_name": "inventory-service",
            "environment": "production",
            "offset_minutes": 10,
            "raw_payload": {
                "namespace": "production",
                "pod": "inventory-service-6c8d4b-pqrst",
                "reason": "CrashLoopBackOff",
                "restart_count": 8,
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "checkout-service success rate dropped to 61%",
            "description": "Checkout funnel success rate 61%, down from 99.2% baseline.",
            "service_name": "checkout-service",
            "environment": "production",
            "offset_minutes": 8,
            "raw_payload": {"monitor_id": 60022},
        },
    ],

    "deployment_failure": [
        {
            "source": "github_actions",
            "severity": AlertSeverity.medium,
            "title": "Deploy workflow: user-service v2.16.0 rollout started",
            "description": "GitHub Actions triggered blue/green deploy of user-service v2.16.0 to production.",
            "service_name": "user-service",
            "environment": "production",
            "offset_minutes": 25,
            "raw_payload": {
                "workflow": "Deploy to Production",
                "run_id": 99887766,
                "version": "v2.16.0",
                "strategy": "blue-green",
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "user-service error rate jumped to 15% post-deploy",
            "description": (
                "Error rate rose from 0.2% to 15.1% within 3 minutes of v2.16.0 "
                "deployment. Errors clustered in /auth/refresh endpoint."
            ),
            "service_name": "user-service",
            "environment": "production",
            "offset_minutes": 20,
            "raw_payload": {
                "monitor_id": 70031,
                "deployment_version": "v2.16.0",
            },
        },
        {
            "source": "sentry",
            "severity": AlertSeverity.critical,
            "title": "JWT decode error: invalid signature – affects all auth token refreshes",
            "description": (
                "jwt.exceptions.InvalidSignatureError in user-service v2.16.0. "
                "JWT_SECRET env var mismatch between pods. "
                "All sessions requiring token refresh are broken."
            ),
            "service_name": "user-service",
            "environment": "production",
            "offset_minutes": 18,
            "raw_payload": {
                "issue_id": "USER-JWT-03",
                "level": "fatal",
                "times_seen": 9821,
                "version": "v2.16.0",
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "api-gateway 401 Unauthorized rate > 20%",
            "description": (
                "api-gateway reporting 21.3% 401 responses. "
                "Downstream user-service JWT validation failing."
            ),
            "service_name": "api-gateway",
            "environment": "production",
            "offset_minutes": 15,
            "raw_payload": {"monitor_id": 70032},
        },
        {
            "source": "github_actions",
            "severity": AlertSeverity.high,
            "title": "Deploy rollback triggered: user-service v2.16.0 → v2.15.3",
            "description": "Automated rollback policy triggered. Reverting to last stable version.",
            "service_name": "user-service",
            "environment": "production",
            "offset_minutes": 12,
            "raw_payload": {
                "workflow": "Rollback",
                "run_id": 99887780,
                "from_version": "v2.16.0",
                "to_version": "v2.15.3",
            },
        },
    ],

    "network_partition": [
        {
            "source": "aws",
            "severity": AlertSeverity.critical,
            "title": "VPC Flow Logs: 100% packet loss between us-east-1a and us-east-1b",
            "description": (
                "Network ACL or routing issue causing complete loss of traffic "
                "between availability zones us-east-1a and us-east-1b."
            ),
            "service_name": "network-infra",
            "environment": "production",
            "offset_minutes": 30,
            "raw_payload": {
                "AlarmName": "VPC-FlowLogs-CrossAZ-Loss",
                "source_az": "us-east-1a",
                "dest_az": "us-east-1b",
                "loss_pct": 100,
            },
        },
        {
            "source": "kubernetes",
            "severity": AlertSeverity.critical,
            "title": "3 nodes NotReady: all in us-east-1b AZ",
            "description": (
                "Nodes ip-10-0-2-11, ip-10-0-2-22, ip-10-0-2-33 transitioned to "
                "NotReady simultaneously. All reside in us-east-1b. "
                "Kubelet unreachable from control plane."
            ),
            "service_name": "k8s-node",
            "environment": "production",
            "offset_minutes": 28,
            "raw_payload": {
                "nodes": ["ip-10-0-2-11", "ip-10-0-2-22", "ip-10-0-2-33"],
                "az": "us-east-1b",
                "condition": "NotReady",
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.critical,
            "title": "orders-service availability 58% – pods unreachable in us-east-1b",
            "description": (
                "6 of 10 orders-service pods are on nodes that are now NotReady. "
                "Remaining 4 pods in us-east-1a are overloaded."
            ),
            "service_name": "orders-service",
            "environment": "production",
            "offset_minutes": 26,
            "raw_payload": {
                "monitor_id": 80041,
                "availability_pct": 58,
            },
        },
        {
            "source": "aws",
            "severity": AlertSeverity.high,
            "title": "RDS Multi-AZ failover initiated – orders-db promoting standby",
            "description": (
                "Aurora detected primary in us-east-1b is unreachable. "
                "Initiating automatic failover to standby in us-east-1a. "
                "Expected downtime: 30–60 seconds."
            ),
            "service_name": "orders-db",
            "environment": "production",
            "offset_minutes": 24,
            "raw_payload": {
                "AlarmName": "RDS-MultiAZ-Failover",
                "cluster": "prod-aurora-cluster",
                "primary_az": "us-east-1b",
                "standby_az": "us-east-1a",
            },
        },
    ],

    "queue_backlog": [
        {
            "source": "aws",
            "severity": AlertSeverity.high,
            "title": "SQS Consumer Lag > 500 messages on payments-processing-queue",
            "description": (
                "payments-processing-queue ApproximateAgeOfOldestMessage is 18 minutes. "
                "Consumer throughput dropped from 120 msg/s to 8 msg/s."
            ),
            "service_name": "payments-service",
            "environment": "production",
            "offset_minutes": 35,
            "raw_payload": {
                "AlarmName": "SQS-ConsumerLag-payments-processing",
                "queue": "payments-processing-queue",
                "message_count": 523,
                "oldest_age_minutes": 18,
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "payments-service worker CPU 98% – all 4 consumer threads saturated",
            "description": (
                "Consumer threads are CPU-bound processing a spike in payment volume. "
                "Thread pool queue depth: 2 048 tasks."
            ),
            "service_name": "payments-service",
            "environment": "production",
            "offset_minutes": 32,
            "raw_payload": {"monitor_id": 90051, "cpu_pct": 98},
        },
        {
            "source": "sentry",
            "severity": AlertSeverity.medium,
            "title": "PaymentTimeoutError: stripe.confirm() exceeded 30 s",
            "description": (
                "Stripe payment confirmation calls timing out. "
                "payments-service is retrying exhausted workers. "
                "375 errors in 20 minutes."
            ),
            "service_name": "payments-service",
            "environment": "production",
            "offset_minutes": 28,
            "raw_payload": {
                "issue_id": "PAY-TIMEOUT-04",
                "level": "error",
                "times_seen": 375,
            },
        },
        {
            "source": "aws",
            "severity": AlertSeverity.critical,
            "title": "SQS Dead-Letter Queue: 289 messages on payments-dlq",
            "description": (
                "289 messages have been moved to the DLQ after 3 failed processing attempts. "
                "These are payment records that must be manually reviewed."
            ),
            "service_name": "payments-service",
            "environment": "production",
            "offset_minutes": 22,
            "raw_payload": {
                "AlarmName": "SQS-DLQ-Depth-payments-dlq",
                "dlq": "payments-dlq",
                "message_count": 289,
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "checkout-service payment step failure rate 24%",
            "description": (
                "1-in-4 checkout payment attempts failing. "
                "Users receiving 'Payment could not be processed' errors."
            ),
            "service_name": "checkout-service",
            "environment": "production",
            "offset_minutes": 18,
            "raw_payload": {"monitor_id": 90052, "failure_rate_pct": 24},
        },
    ],
}


def build_alerts_for_scenario(scenario_name: str) -> list[dict[str, Any]]:
    """
    Return a list of AlertCreate-compatible dicts for the given scenario.
    Timestamps are computed relative to now so alerts appear recent.
    Adds a small random jitter (±90 s) so repeated calls look different.
    """
    templates = SCENARIOS.get(scenario_name)
    if not templates:
        raise ValueError(
            f"Unknown scenario '{scenario_name}'. "
            f"Available: {', '.join(SCENARIOS.keys())}"
        )

    alerts = []
    for tpl in templates:
        jitter = random.uniform(-1.5, 1.5)  # ±90 seconds
        offset = tpl.get("offset_minutes", 0) + jitter
        ts = (_NOW - timedelta(minutes=offset)).isoformat()

        alerts.append(
            {
                "source": tpl["source"],
                "severity": tpl["severity"].value
                if isinstance(tpl["severity"], AlertSeverity)
                else tpl["severity"],
                "title": tpl["title"],
                "description": tpl.get("description"),
                "service_name": tpl["service_name"],
                "environment": tpl.get("environment", "production"),
                "timestamp": ts,
                "status": AlertStatus.open.value,
                "raw_payload": tpl.get("raw_payload"),
            }
        )
    return alerts


AVAILABLE_SCENARIOS = list(SCENARIOS.keys())
