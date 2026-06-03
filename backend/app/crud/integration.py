from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import Integration, IntegrationProvider, IntegrationStatus
from app.schemas.integration import IntegrationCreate, IntegrationUpdate

# Display names for each provider
PROVIDER_NAMES: dict[IntegrationProvider, str] = {
    IntegrationProvider.aws_cloudwatch: "AWS CloudWatch",
    IntegrationProvider.datadog: "Datadog",
    IntegrationProvider.sentry: "Sentry",
    IntegrationProvider.github_actions: "GitHub Actions",
    IntegrationProvider.kubernetes: "Kubernetes",
    IntegrationProvider.slack: "Slack",
}

# Default mock configs shown when connected
PROVIDER_DEFAULT_CONFIGS: dict[IntegrationProvider, dict] = {
    IntegrationProvider.aws_cloudwatch: {
        "region": "us-east-1",
        "account_id": "123456789012",
        "alarm_prefix": "aiops-",
        "sample_payload": {
            "AlarmName": "RDS-HighCPU",
            "NewStateValue": "ALARM",
            "Region": "us-east-1",
            "Trigger": {"MetricName": "CPUUtilization", "Threshold": 95},
        },
    },
    IntegrationProvider.datadog: {
        "site": "datadoghq.com",
        "api_key_hint": "dd_api_****",
        "tags": ["env:production", "team:platform"],
        "sample_payload": {
            "monitor_id": 12345,
            "monitor_name": "High error rate",
            "query": "avg(last_5m):sum:trace.errors{env:production} > 5",
            "tags": ["env:production", "service:api"],
        },
    },
    IntegrationProvider.sentry: {
        "org_slug": "your-org",
        "dsn_hint": "https://****@sentry.io/",
        "environments": ["production", "staging"],
        "sample_payload": {
            "project": "backend",
            "issue_id": "PROJ-1234",
            "level": "error",
            "times_seen": 142,
            "culprit": "app/services/payment.py in process_payment",
        },
    },
    IntegrationProvider.github_actions: {
        "org": "your-org",
        "repositories": ["backend", "frontend", "infra"],
        "sample_payload": {
            "workflow": "Deploy to Production",
            "run_id": 9876543210,
            "conclusion": "failure",
            "repository": "your-org/backend",
            "branch": "main",
            "commit_sha": "a1b2c3d",
        },
    },
    IntegrationProvider.kubernetes: {
        "cluster": "prod-eks-cluster",
        "namespaces": ["production", "staging"],
        "sample_payload": {
            "namespace": "production",
            "pod": "api-server-7d9f8b-xvk2p",
            "reason": "OOMKilled",
            "restart_count": 5,
            "memory_limit": "512Mi",
            "node": "ip-10-0-1-42.ec2.internal",
        },
    },
    IntegrationProvider.slack: {
        "workspace": "your-workspace",
        "channel": "#incidents",
        "notify_on": ["critical", "high"],
        "sample_payload": {
            "channel": "#incidents",
            "text": "🚨 New incident: High error rate in checkout-service",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "*Alert*: p99 latency > 8s"}}],
        },
    },
}


async def list_integrations(db: AsyncSession, org_id: int) -> list[Integration]:
    rows = (
        await db.execute(
            select(Integration)
            .where(Integration.organization_id == org_id)
            .order_by(Integration.created_at.asc())
        )
    ).scalars().all()
    return list(rows)


async def get_integration(db: AsyncSession, integration_id: int) -> Integration | None:
    return (
        await db.execute(select(Integration).where(Integration.id == integration_id))
    ).scalar_one_or_none()


async def create_integration(
    db: AsyncSession, payload: IntegrationCreate, org_id: int
) -> Integration:
    name = payload.name or PROVIDER_NAMES.get(payload.provider, payload.provider.value)
    integration = Integration(
        organization_id=org_id,
        provider=payload.provider,
        name=name,
        status=IntegrationStatus.disconnected,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


async def update_integration(
    db: AsyncSession, integration: Integration, payload: IntegrationUpdate
) -> Integration:
    if payload.status is not None:
        integration.status = payload.status
        if payload.status == IntegrationStatus.connected:
            integration.last_sync = datetime.now(tz=timezone.utc)
            if not integration.config:
                integration.config = PROVIDER_DEFAULT_CONFIGS.get(integration.provider)
        elif payload.status == IntegrationStatus.disconnected:
            integration.config = None
            integration.last_sync = None
    if payload.name is not None:
        integration.name = payload.name
    if payload.config is not None:
        integration.config = payload.config
    await db.commit()
    await db.refresh(integration)
    return integration


async def touch_last_sync(db: AsyncSession, integration: Integration) -> None:
    integration.last_sync = datetime.now(tz=timezone.utc)
    await db.commit()
