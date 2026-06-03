"""
Realistic per-provider alert templates for the integration test-alert feature.
Each provider maps to a list of alert dicts; one is picked randomly on each call.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from app.models.alert import AlertSeverity, AlertStatus
from app.models.integration import IntegrationProvider

_NOW = datetime.now(tz=timezone.utc)
_TS = _NOW.isoformat()


PROVIDER_ALERTS: dict[IntegrationProvider, list[dict[str, Any]]] = {

    IntegrationProvider.aws_cloudwatch: [
        {
            "source": "aws",
            "severity": AlertSeverity.critical,
            "title": "RDS Aurora CPU Utilisation > 95% – prod-aurora-cluster",
            "description": (
                "Aurora PostgreSQL cluster prod-aurora-cluster has sustained CPU above 95% "
                "for 10 minutes. Slow query log shows N+1 queries from orders-service."
            ),
            "service_name": "orders-db",
            "environment": "production",
            "raw_payload": {
                "AlarmName": "RDS-HighCPU-prod-aurora",
                "AWSAccountId": "123456789012",
                "Region": "us-east-1",
                "NewStateValue": "ALARM",
                "Trigger": {"MetricName": "CPUUtilization", "Namespace": "AWS/RDS", "Threshold": 95.0},
            },
        },
        {
            "source": "aws",
            "severity": AlertSeverity.high,
            "title": "ALB 5xx Error Rate > 8% on api-gateway target group",
            "description": (
                "Application Load Balancer api-gateway-tg reporting 8.7% HTTP 5xx over last 5 min. "
                "3 of 6 backend instances failing health checks."
            ),
            "service_name": "api-gateway",
            "environment": "production",
            "raw_payload": {
                "AlarmName": "ALB-5xxRate-api-gateway",
                "Region": "us-east-1",
                "Trigger": {"MetricName": "HTTPCode_ELB_5XX_Count", "Threshold": 8.0},
            },
        },
        {
            "source": "aws",
            "severity": AlertSeverity.critical,
            "title": "SQS Dead-Letter Queue: 312 messages on payments-dlq",
            "description": (
                "payments-dlq has accumulated 312 unprocessable messages. "
                "Consumer has been rejecting messages for 25 minutes."
            ),
            "service_name": "payments-service",
            "environment": "production",
            "raw_payload": {
                "AlarmName": "SQS-DLQ-Depth-payments-dlq",
                "Region": "us-east-1",
                "Trigger": {"MetricName": "ApproximateNumberOfMessagesNotVisible", "Threshold": 100},
            },
        },
        {
            "source": "aws",
            "severity": AlertSeverity.high,
            "title": "RDS Multi-AZ failover in progress – orders-db",
            "description": (
                "Aurora detected primary node unreachable. Initiating failover to standby in us-east-1a. "
                "Estimated downtime: 30–60 s."
            ),
            "service_name": "orders-db",
            "environment": "production",
            "raw_payload": {
                "AlarmName": "RDS-MultiAZ-Failover",
                "Region": "us-east-1",
                "cluster": "prod-aurora-cluster",
            },
        },
    ],

    IntegrationProvider.datadog: [
        {
            "source": "datadog",
            "severity": AlertSeverity.critical,
            "title": "p99 Latency spike: checkout-service > 9 000 ms",
            "description": (
                "checkout-service p99 response time has exceeded 9 s for 5 consecutive minutes. "
                "APM traces show inventory-service downstream calls timing out."
            ),
            "service_name": "checkout-service",
            "environment": "production",
            "raw_payload": {
                "monitor_id": 4821903,
                "monitor_name": "checkout-service p99 latency",
                "query": "avg(last_5m):p99:trace.http.request{service:checkout-service} > 9000",
                "tags": ["env:production", "service:checkout-service"],
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "Error rate elevated: inventory-service 14% errors",
            "description": (
                "inventory-service returning errors on 14.2% of requests. "
                "Errors concentrated in GET /v2/products. Correlates with memory pressure."
            ),
            "service_name": "inventory-service",
            "environment": "production",
            "raw_payload": {
                "monitor_id": 4821704,
                "monitor_name": "inventory-service error rate",
                "query": "sum(last_5m):sum:trace.errors{service:inventory-service}.as_count() / sum:trace.hits{service:inventory-service}.as_count() > 0.14",
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.high,
            "title": "checkout-service success rate dropped to 67%",
            "description": "Checkout funnel success rate 67.3%, down from 99.1% 30-day baseline.",
            "service_name": "checkout-service",
            "environment": "production",
            "raw_payload": {
                "monitor_id": 4822001,
                "monitor_name": "checkout success rate",
                "tags": ["env:production", "service:checkout-service"],
            },
        },
        {
            "source": "datadog",
            "severity": AlertSeverity.medium,
            "title": "Redis cache hit ratio dropped to 51% on session-cache",
            "description": (
                "session-cache Redis cluster hit ratio is 51%, down from 91% baseline. "
                "Memory eviction storm suspected — maxmemory-policy=allkeys-lru."
            ),
            "service_name": "session-cache",
            "environment": "production",
            "raw_payload": {
                "monitor_id": 4820011,
                "monitor_name": "Redis cache hit ratio",
                "tags": ["env:production", "service:session-cache"],
            },
        },
    ],

    IntegrationProvider.sentry: [
        {
            "source": "sentry",
            "severity": AlertSeverity.critical,
            "title": "UnhandledPromiseRejection: Cannot read properties of null (reading 'price')",
            "description": (
                "TypeError in checkout-service/src/cart/CartService.ts:142. "
                "Null product returned from inventory-service during restart window. "
                "Affecting 1,840 users in the last 15 minutes."
            ),
            "service_name": "checkout-service",
            "environment": "production",
            "raw_payload": {
                "project": "checkout-service",
                "issue_id": "CHECKOUT-4F2B",
                "culprit": "checkout-service/src/cart/CartService.ts in processCart",
                "level": "fatal",
                "times_seen": 1840,
                "first_seen": _TS,
            },
        },
        {
            "source": "sentry",
            "severity": AlertSeverity.critical,
            "title": "DatabaseConnectionError: max_connections exceeded – orders-service",
            "description": (
                "psycopg2.OperationalError in orders-service: remaining connection slots reserved. "
                "Connection pool exhausted. 1,023 users cannot complete orders."
            ),
            "service_name": "orders-service",
            "environment": "production",
            "raw_payload": {
                "project": "orders-service",
                "issue_id": "ORDERS-DB-CONN-03",
                "level": "fatal",
                "times_seen": 1023,
            },
        },
        {
            "source": "sentry",
            "severity": AlertSeverity.high,
            "title": "PaymentWebhookParseError: unexpected field in Stripe payload",
            "description": (
                "Stripe webhook schema mismatch in payments-service. "
                "Validator rejecting new 'risk_level' field added in Stripe API v2025-06."
            ),
            "service_name": "payments-service",
            "environment": "production",
            "raw_payload": {
                "project": "payments-service",
                "issue_id": "PAYMENTS-WEBHOOK-05",
                "level": "error",
                "times_seen": 408,
            },
        },
        {
            "source": "sentry",
            "severity": AlertSeverity.high,
            "title": "jwt.exceptions.InvalidSignatureError – token refresh broken",
            "description": (
                "JWT_SECRET env var mismatch after rolling deployment of user-service v2.17.0. "
                "All token refresh calls failing. 9,200 active sessions affected."
            ),
            "service_name": "user-service",
            "environment": "production",
            "raw_payload": {
                "project": "user-service",
                "issue_id": "USER-JWT-06",
                "level": "fatal",
                "times_seen": 9200,
                "version": "v2.17.0",
            },
        },
    ],

    IntegrationProvider.github_actions: [
        {
            "source": "github_actions",
            "severity": AlertSeverity.high,
            "title": "CI Pipeline failure: orders-service main branch – 18 tests failed",
            "description": (
                "Workflow 'Deploy to Production' failed at 'Run integration tests'. "
                "18 DB connection pool tests failing — staging DB under production load."
            ),
            "service_name": "orders-service",
            "environment": "ci",
            "raw_payload": {
                "workflow": "Deploy to Production",
                "run_id": 11234567891,
                "conclusion": "failure",
                "repository": "acme-corp/orders-service",
                "branch": "main",
                "commit_sha": "b4e2f1a",
                "failed_steps": ["Run integration tests"],
            },
        },
        {
            "source": "github_actions",
            "severity": AlertSeverity.critical,
            "title": "Deploy rollback triggered: checkout-service v3.2.1 → v3.2.0",
            "description": (
                "Automated canary health check failed within 5 minutes of v3.2.1 deployment. "
                "Error rate exceeded 2% threshold. Rolling back to v3.2.0."
            ),
            "service_name": "checkout-service",
            "environment": "production",
            "raw_payload": {
                "workflow": "Canary Rollback",
                "run_id": 11234567999,
                "from_version": "v3.2.1",
                "to_version": "v3.2.0",
                "trigger": "canary_error_rate_exceeded",
                "error_rate_pct": 2.8,
            },
        },
        {
            "source": "github_actions",
            "severity": AlertSeverity.medium,
            "title": "Security scan: 4 HIGH CVEs in inventory-service base image",
            "description": (
                "Trivy container scan found 4 HIGH severity CVEs in python:3.11-slim. "
                "Recommendation: upgrade to python:3.12-slim."
            ),
            "service_name": "inventory-service",
            "environment": "ci",
            "raw_payload": {
                "workflow": "Security Scan",
                "run_id": 11230001235,
                "tool": "trivy",
                "critical_count": 0,
                "high_count": 4,
                "base_image": "python:3.11-slim",
            },
        },
    ],

    IntegrationProvider.kubernetes: [
        {
            "source": "kubernetes",
            "severity": AlertSeverity.critical,
            "title": "OOMKilled: inventory-service pod restarted 9 times – CrashLoopBackOff",
            "description": (
                "Pod inventory-service-7d9f8b-abc12 in namespace production is in CrashLoopBackOff. "
                "Memory limit 512Mi exceeded. Unbounded cache growth detected via heap profiler."
            ),
            "service_name": "inventory-service",
            "environment": "production",
            "raw_payload": {
                "namespace": "production",
                "pod": "inventory-service-7d9f8b-abc12",
                "container": "inventory-service",
                "reason": "CrashLoopBackOff",
                "restart_count": 9,
                "memory_limit": "512Mi",
                "node": "ip-10-0-1-42.ec2.internal",
            },
        },
        {
            "source": "kubernetes",
            "severity": AlertSeverity.high,
            "title": "HPA unable to scale checkout-service – maxReplicas=10 reached",
            "description": (
                "HPA checkout-service-hpa is at maxReplicas=10. CPU target 70% exceeded (current 97%). "
                "No new nodes available in cluster autoscaler queue."
            ),
            "service_name": "checkout-service",
            "environment": "production",
            "raw_payload": {
                "namespace": "production",
                "hpa": "checkout-service-hpa",
                "current_replicas": 10,
                "desired_replicas": 15,
                "max_replicas": 10,
                "current_cpu": "97%",
            },
        },
        {
            "source": "kubernetes",
            "severity": AlertSeverity.critical,
            "title": "3 nodes NotReady: all in us-east-1b – possible AZ outage",
            "description": (
                "Nodes ip-10-0-2-11, ip-10-0-2-22, ip-10-0-2-33 simultaneously transitioned to NotReady. "
                "All reside in us-east-1b. Kubelet unreachable from control plane."
            ),
            "service_name": "k8s-node",
            "environment": "production",
            "raw_payload": {
                "nodes": ["ip-10-0-2-11", "ip-10-0-2-22", "ip-10-0-2-33"],
                "az": "us-east-1b",
                "condition": "NotReady",
                "kubelet_status": "unreachable",
            },
        },
        {
            "source": "kubernetes",
            "severity": AlertSeverity.high,
            "title": "PVC Pending: orders-service-pvc-new – no storage in us-east-1a",
            "description": "PVC stuck Pending for 18 minutes. StorageClass gp3-encrypted has no available volumes in AZ.",
            "service_name": "orders-service",
            "environment": "production",
            "raw_payload": {
                "namespace": "production",
                "pvc": "orders-service-pvc-new",
                "storage_class": "gp3-encrypted",
                "requested": "20Gi",
                "az": "us-east-1a",
            },
        },
    ],

    IntegrationProvider.slack: [
        {
            "source": "slack",
            "severity": AlertSeverity.high,
            "title": "Slack alert: On-call reports checkout-service unresponsive",
            "description": (
                "On-call engineer @alex reported in #incidents: "
                "'checkout-service is returning 502s — customers can't complete purchases. "
                "Alerting now, investigating root cause.'"
            ),
            "service_name": "checkout-service",
            "environment": "production",
            "raw_payload": {
                "channel": "#incidents",
                "user": "alex",
                "text": "checkout-service is returning 502s — customers can't complete purchases.",
                "triggered_by": "manual",
            },
        },
        {
            "source": "slack",
            "severity": AlertSeverity.critical,
            "title": "Slack alert: payments-service down – all transactions failing",
            "description": (
                "Critical report from #incidents: "
                "'payments-service is completely down. No transactions processing for the past 8 minutes. "
                "Revenue impact $12k/min.'"
            ),
            "service_name": "payments-service",
            "environment": "production",
            "raw_payload": {
                "channel": "#incidents",
                "user": "oncall-bot",
                "text": "payments-service completely down. No transactions processing.",
                "triggered_by": "pagerduty_webhook",
            },
        },
        {
            "source": "slack",
            "severity": AlertSeverity.medium,
            "title": "Slack alert: user-service elevated latency reported by QA",
            "description": (
                "QA team reported in #platform-alerts: "
                "'user-service /auth/login endpoint taking 4s+. "
                "Started after 14:30 UTC deploy.'"
            ),
            "service_name": "user-service",
            "environment": "production",
            "raw_payload": {
                "channel": "#platform-alerts",
                "user": "qa-bot",
                "text": "user-service /auth/login taking 4s+",
                "triggered_by": "manual",
            },
        },
    ],
}


def pick_test_alert(provider: IntegrationProvider) -> dict:
    """Return a random AlertCreate-compatible dict for the given provider."""
    templates = PROVIDER_ALERTS.get(provider, [])
    if not templates:
        raise ValueError(f"No alert templates for provider {provider}")
    tpl = random.choice(templates)
    now = datetime.now(tz=timezone.utc)
    return {
        "source": tpl["source"],
        "severity": tpl["severity"].value if isinstance(tpl["severity"], AlertSeverity) else tpl["severity"],
        "title": tpl["title"],
        "description": tpl.get("description"),
        "service_name": tpl["service_name"],
        "environment": tpl.get("environment", "production"),
        "timestamp": now.isoformat(),
        "status": "open",
        "raw_payload": tpl.get("raw_payload"),
    }
