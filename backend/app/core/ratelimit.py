"""
Shared rate limiter (slowapi).

Per-IP limits applied to the abuse-prone endpoints: auth (credential
stuffing / signup spam), alert ingestion and demo generation (DB floods),
and AI analysis (OpenAI spend).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])

# Limits, kept in one place so they're easy to tune
AUTH_LOGIN_LIMIT = "10/minute"
AUTH_SIGNUP_LIMIT = "5/hour"
ALERT_INGEST_LIMIT = "120/minute"
DEMO_GENERATE_LIMIT = "10/minute"
ANALYZE_LIMIT = "10/minute"
