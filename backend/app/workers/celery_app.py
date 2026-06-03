"""
Celery application factory.

Two task queues:
  alerts    – high-priority, short-lived  (alert processing, correlation)
  analysis  – lower-priority, longer      (AI analysis, can be slow)
  default   – catch-all

Beat schedule (periodic tasks):
  generate-demo-alerts   – fires every DEMO_ALERT_INTERVAL_SECONDS seconds
                           (only active when DEMO_PERIODIC_ALERTS=true)
  worker-heartbeat       – lightweight ping every 30 s to prove the worker is alive
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.core.config import settings

# ── App ───────────────────────────────────────────────────────────────────────

celery_app = Celery(
    "aiops",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

# ── Queues / routing ──────────────────────────────────────────────────────────

default_exchange = Exchange("default", type="direct")
alerts_exchange  = Exchange("alerts",  type="direct")
analysis_exchange = Exchange("analysis", type="direct")

celery_app.conf.task_queues = (
    Queue("default",  default_exchange,  routing_key="default"),
    Queue("alerts",   alerts_exchange,   routing_key="alerts"),
    Queue("analysis", analysis_exchange, routing_key="analysis"),
)
celery_app.conf.task_default_queue    = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

celery_app.conf.task_routes = {
    "tasks.process_alert":        {"queue": "alerts",   "routing_key": "alerts"},
    "tasks.correlate_alert":      {"queue": "alerts",   "routing_key": "alerts"},
    "tasks.analyze_incident_bg":  {"queue": "analysis", "routing_key": "analysis"},
    "tasks.generate_demo_alerts": {"queue": "default",  "routing_key": "default"},
    "tasks.worker_heartbeat":     {"queue": "default",  "routing_key": "default"},
}

# ── Serialisation & time ──────────────────────────────────────────────────────

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Timeouts
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    # Visibility / retries
    task_acks_late=True,             # re-queue on worker crash
    worker_prefetch_multiplier=1,    # one task at a time per worker (fairness)
    task_reject_on_worker_lost=True, # re-queue if worker dies mid-task
    # Results expire after 24 h (we don't need them long-term)
    result_expires=86400,
)

# ── Beat schedule (periodic tasks) ───────────────────────────────────────────

beat_schedule: dict = {
    "worker-heartbeat": {
        "task": "tasks.worker_heartbeat",
        "schedule": 30.0,   # every 30 seconds
        "options": {"queue": "default"},
    },
}

if settings.DEMO_PERIODIC_ALERTS:
    beat_schedule["generate-demo-alerts"] = {
        "task": "tasks.generate_demo_alerts",
        "schedule": float(settings.DEMO_ALERT_INTERVAL_SECONDS),
        "options": {"queue": "default"},
    }

celery_app.conf.beat_schedule = beat_schedule
