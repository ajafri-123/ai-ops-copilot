# AI Operations Copilot

> A multi-tenant AI incident-response platform (portfolio project) that ingests alerts, correlates them into incidents, and uses GPT-4o-mini to generate root-cause analysis and remediation playbooks — all delivered in real time. The included Docker setup is development-grade; see the deployment notes before exposing it anywhere public.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15.3-black?logo=next.js)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Feature Highlights](#2-feature-highlights)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Project Structure](#5-project-structure)
6. [Quick Start](#6-quick-start)
7. [Configuration Reference](#7-configuration-reference)
8. [API Reference](#8-api-reference)
9. [WebSocket Events](#9-websocket-events)
10. [Running Tests](#10-running-tests)
11. [Deployment Notes](#11-deployment-notes)
12. [Troubleshooting](#12-troubleshooting)
13. [Roadmap](#13-roadmap)

---

## 1. Overview

Engineering teams lose hours every incident because alerts arrive in isolation, context is scattered, and on-call engineers must manually piece together root cause under pressure. **AI Operations Copilot** solves this by:

- **Ingesting alerts** from any source via a REST API, plus simulated integrations (AWS CloudWatch, Datadog, Sentry, GitHub Actions, Kubernetes, Slack).
- **Auto-correlating** related alerts into a single incident using a rule-based correlation engine.
- **Generating AI analysis** — root-cause hypothesis, blast radius, and a step-by-step remediation playbook — powered by OpenAI GPT-4o-mini (with a deterministic mock fallback when no API key is configured).
- **Streaming updates in real time** to all connected dashboards via WebSocket.
- **Enforcing tenant isolation** so multiple teams can share one deployment without data leakage.

### Demo Credentials

| Field    | Value              |
|----------|--------------------|
| Email    | `demo@example.com` |
| Password | `demo1234`         |

> The demo account and a full set of pre-seeded alerts and incidents are created automatically on first startup.

---

## 2. Feature Highlights

| Feature | Details |
|---|---|
| **Alert Ingestion** | REST endpoint with optional timestamp, severity, service tags, and arbitrary JSON payload |
| **Correlation Engine** | Groups alerts by time window + overlapping service tags; creates or updates incidents automatically |
| **AI Analysis** | GPT-4o-mini generates structured root-cause analysis, affected services list, and remediation steps |
| **Service Dependency Graph** | Interactive node-link diagram built with React Flow; edges derived from service metadata |
| **Real-Time Dashboard** | WebSocket push for new alerts and incident updates; auto-reconnect with exponential back-off |
| **Multi-Tenancy** | Every DB row is scoped to an `organization_id`; JWT carries org context; FK constraints enforce isolation |
| **Async Task Queue** | Celery workers handle heavy analysis tasks; Celery Beat runs periodic demo-alert generation |
| **Flower Monitoring** | Built-in Celery task dashboard at `localhost:5555` |
| **Automated tests** | pytest (async) for backend; Jest + React Testing Library for frontend — run in CI on every push |
| **Zero-Key Demo** | No OpenAI API key needed — mock analyzer produces realistic, deterministic output |

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser / Client                        │
│              Next.js 15 (App Router, RSC, Tailwind)             │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP + WebSocket
┌────────────────────────▼────────────────────────────────────────┐
│                    FastAPI  (port 8000)                         │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  REST API  │  │  WebSocket   │  │   Auth Middleware       │  │
│  │  /api/v1   │  │  /api/v1/ws  │  │   JWT + Org Scoping    │  │
│  └─────┬──────┘  └──────┬───────┘  └────────────────────────┘  │
│        │                │                                       │
│  ┌─────▼──────────────────────────────────────────────────┐    │
│  │              Service Layer                             │    │
│  │  CorrelationEngine  │  AIService  │  AnalysisPipeline  │    │
│  └─────┬──────────────────────────────────────────────────┘    │
└────────┼────────────────────────────────────────────────────────┘
         │ SQLAlchemy 2 (async)           │ Celery tasks
┌────────▼──────────┐          ┌──────────▼─────────────┐
│   PostgreSQL 16   │          │   Redis 7              │
│  (primary store)  │          │  (broker + pub/sub)    │
└───────────────────┘          └────────────────────────┘
                                         │
                               ┌─────────▼──────────────┐
                               │  Celery Worker / Beat  │
                               │  (analysis, demo gen)  │
                               └────────────────────────┘
```

### Data Flow — Alert to Incident

```
1. POST /api/v1/alerts          → Alert saved to DB
2. Correlation Engine           → Alert matched or grouped into Incident
3. Celery task dispatched       → AIService.analyze_incident() called
4. OpenAI (or mock) responds    → AnalysisResult stored on Incident
5. WebSocket broadcast          → All connected dashboards updated instantly
```

### Multi-Tenancy Model

```
Organization
    └── Users (via Membership: owner | admin | member)
    └── Alerts       (organization_id FK)
    └── Incidents    (organization_id FK)
    └── Integrations (organization_id FK)
```

Every database query is filtered by `org_id` extracted from the JWT token. The application layer enforces this through the `get_auth` FastAPI dependency; the database layer enforces it through foreign-key constraints.

---

## 4. Tech Stack

### Backend

| Library | Version | Purpose |
|---|---|---|
| FastAPI | 0.115.5 | Async REST API + WebSocket |
| Uvicorn | 0.32.1 | ASGI server |
| SQLAlchemy | 2.0.36 | Async ORM |
| asyncpg | 0.30.0 | PostgreSQL async driver |
| Pydantic | 2.10.3 | Request/response validation |
| pydantic-settings | 2.6.1 | Environment-based config |
| Celery | 5.4.0 | Distributed task queue |
| Redis (py) | 5.2.1 | Broker + cache client |
| OpenAI | 1.57.4 | GPT-4o-mini integration |
| python-jose | 3.3.0 | JWT encoding/decoding |
| passlib + bcrypt | 1.7.4 / 4.0.1 | Password hashing |
| pytest-asyncio | 0.25.0 | Async test runner |

### Frontend

| Library | Version | Purpose |
|---|---|---|
| Next.js | 15.3.9 | React framework (App Router, SSR, RSC) |
| React | 19.0.0 | UI library |
| TypeScript | 5 | Static typing |
| Tailwind CSS | 3.4.1 | Utility-first styling |
| @xyflow/react | 12.3.6 | Service dependency graph |
| Jest + RTL | 29 / 16 | Unit and integration tests |

### Infrastructure

| Service | Image | Port |
|---|---|---|
| PostgreSQL | postgres:16-alpine | 5432 |
| Redis | redis:7-alpine | 6379 |
| Flower (Celery UI) | (built from backend) | 5555 |

---

## 5. Project Structure

```
ai-ops-copilot/
├── backend/
│   ├── app/
│   │   ├── api/v1/               # Route handlers
│   │   │   ├── alerts.py         # Alert ingestion & listing
│   │   │   ├── incidents.py      # Incident CRUD + analysis trigger
│   │   │   ├── auth.py           # Signup, login, /me
│   │   │   ├── analysis.py       # On-demand AI analysis
│   │   │   ├── integrations.py   # Integration CRUD
│   │   │   ├── graph.py          # Service dependency graph data
│   │   │   ├── websocket.py      # WebSocket endpoint
│   │   │   └── health.py         # Health check
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic-settings config
│   │   │   ├── database.py       # Async SQLAlchemy engine + session
│   │   │   ├── security.py       # JWT + bcrypt helpers
│   │   │   ├── deps.py           # FastAPI dependencies (auth context)
│   │   │   ├── redis.py          # Redis client factory
│   │   │   ├── ws_manager.py     # WebSocket connection manager
│   │   │   └── seed.py           # Demo data seeder
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── alert.py
│   │   │   ├── incident.py
│   │   │   ├── organization.py
│   │   │   ├── user.py
│   │   │   ├── membership.py
│   │   │   ├── integration.py
│   │   │   └── service_dependency.py
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── crud/                 # Async DB operations (no business logic)
│   │   ├── services/
│   │   │   ├── correlation_engine.py   # Alert → Incident grouping
│   │   │   ├── ai_service.py           # OpenAI + mock fallback
│   │   │   ├── analysis_pipeline.py    # Orchestrates analysis steps
│   │   │   ├── integration_alerts.py   # Pulls alerts from integrations
│   │   │   └── demo_generator.py       # Scripted demo scenarios
│   │   ├── workers/
│   │   │   ├── celery_app.py     # Celery app + queue config
│   │   │   └── tasks.py          # Task definitions
│   │   ├── tests/                # ~80 pytest tests
│   │   └── main.py               # App entry point (lifespan: migrate + seed)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx              # Landing page
│   │   │   ├── login/page.tsx
│   │   │   ├── signup/page.tsx
│   │   │   ├── dashboard/page.tsx    # Main dashboard
│   │   │   ├── incidents/[id]/page.tsx
│   │   │   └── integrations/page.tsx
│   │   ├── components/
│   │   │   ├── AlertFeed.tsx
│   │   │   ├── IncidentCard.tsx
│   │   │   ├── DemoLauncher.tsx
│   │   │   ├── StatsBar.tsx
│   │   │   ├── ConnectionStatus.tsx
│   │   │   └── incident/
│   │   │       ├── AIPanel.tsx
│   │   │       ├── IncidentTimeline.tsx
│   │   │       ├── ServiceGraphLoader.tsx
│   │   │       └── AlertDrawer.tsx
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts   # Auto-reconnect WebSocket hook
│   │   └── lib/
│   │       ├── api.ts            # Typed API client (SSR-aware)
│   │       ├── auth.ts           # Token storage + refresh helpers
│   │       └── types.ts          # Shared TypeScript interfaces
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── LICENSE
```

---

## 6. Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Compose)
- Git

> **No API keys required.** Without an `OPENAI_API_KEY`, the system uses a built-in mock analyzer that returns realistic, deterministic responses — perfect for demos and development.

### 1 — Clone and Configure

```bash
git clone https://github.com/your-username/ai-ops-copilot.git
cd ai-ops-copilot
cp .env.example .env
```

The defaults in `.env.example` work out of the box. Optionally add your OpenAI key for real GPT-4o-mini analysis:

```bash
# .env  (optional)
OPENAI_API_KEY=sk-...
```

### 2 — Start All Services

```bash
docker compose up --build
```

First boot takes ~2 minutes (image pulls + database migrations + seed data). Subsequent starts are much faster.

| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost:3000 | — |
| Backend API | http://localhost:8000/docs | — |
| Flower (Celery) | http://localhost:5555 | admin / admin |

### 3 — Log In

Navigate to http://localhost:3000/login and sign in with the demo account:

```
Email:    demo@example.com
Password: demo1234
```

### 4 — Trigger a Demo Scenario

On the dashboard, click **Launch Demo** to fire a scripted sequence of correlated alerts. Within seconds you will see:

1. Alerts stream into the **Alert Feed** panel.
2. The **Correlation Engine** groups them into an incident.
3. The **AI Panel** populates with root-cause analysis and remediation steps.
4. The **Service Graph** highlights affected nodes.

### Ingest an Alert Manually

```bash
curl -X POST http://localhost:8000/api/v1/alerts \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "High CPU on payment-service",
    "severity": "critical",
    "source": "prometheus",
    "service": "payment-service",
    "tags": ["payment-service", "cpu", "prod"],
    "payload": {"cpu_percent": 97.4, "host": "prod-payments-3"}
  }'
```

Obtain a JWT via `POST /api/v1/auth/login` (see [API Reference](#8-api-reference)).

---

## 7. Configuration Reference

All variables live in `.env` (copy from `.env.example`). The backend refuses to start in production mode if `SECRET_KEY` is still set to `change-me`.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me` | JWT signing secret — **must be changed in production** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Token lifetime (7 days) |
| `POSTGRES_DB` | `aiops` | Database name |
| `POSTGRES_USER` | `aiops` | Database user |
| `POSTGRES_PASSWORD` | `changeme` | Database password |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `OPENAI_API_KEY` | *(empty)* | Optional — falls back to mock if unset |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used for analysis |
| `DEBUG` | `false` | Enables verbose logging |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `CELERY_CONCURRENCY` | `4` | Worker concurrency |
| `DEMO_PERIODIC_ALERTS` | `false` | Auto-generate demo alerts on a schedule |
| `DEMO_ALERT_INTERVAL_SECONDS` | `120` | Interval for periodic demo alerts |
| `AUTO_ANALYZE_NEW_INCIDENTS` | `false` | Trigger AI analysis automatically on incident creation |
| `FLOWER_USER` | `admin` | Flower dashboard username |
| `FLOWER_PASSWORD` | `admin` | Flower dashboard password |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API base URL (used by browser) |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | WebSocket base URL (used by browser) |
| `INTERNAL_API_URL` | `http://backend:8000` | API URL for Next.js server-side fetching inside Docker |

---

## 8. API Reference

Interactive Swagger UI is available at **http://localhost:8000/docs**.

### Authentication

#### Sign Up

```http
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "you@example.com",
  "password": "yourpassword",
  "org_name": "Acme Corp"
}
```

Response:
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

Creating an account automatically creates an `Organization` and sets you as `owner`.

#### Log In

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "you@example.com",
  "password": "yourpassword"
}
```

#### Current User

```http
GET /api/v1/auth/me
Authorization: Bearer <jwt>
```

---

### Alerts

#### Ingest an Alert

```http
POST /api/v1/alerts
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "title": "string",
  "severity": "critical | high | medium | low | info",
  "source": "string",
  "service": "string",
  "tags": ["string"],
  "payload": {},
  "timestamp": "2026-01-01T00:00:00Z"
}
```

The `timestamp` field is optional; if omitted the server sets it to the current UTC time.

#### List Alerts

```http
GET /api/v1/alerts?limit=50&offset=0&severity=critical
Authorization: Bearer <jwt>
```

---

### Incidents

#### List Incidents

```http
GET /api/v1/incidents?limit=20&offset=0&status=open
Authorization: Bearer <jwt>
```

#### Get Incident

```http
GET /api/v1/incidents/{incident_id}
Authorization: Bearer <jwt>
```

Response includes the full alert list, AI analysis, and service graph data.

#### Update Incident Status

```http
PATCH /api/v1/incidents/{incident_id}
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "status": "investigating | resolved | closed",
  "title": "optional new title"
}
```

#### Trigger AI Analysis

```http
POST /api/v1/incidents/{incident_id}/analyze
Authorization: Bearer <jwt>
```

Enqueues a Celery task; the result is pushed to connected clients via WebSocket when complete.

---

### Integrations

#### List Integrations

```http
GET /api/v1/integrations
Authorization: Bearer <jwt>
```

#### Create Integration

```http
POST /api/v1/integrations
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "name": "Production PagerDuty",
  "type": "pagerduty | datadog | prometheus",
  "config": {
    "api_key": "...",
    "service_id": "..."
  }
}
```

#### Sync Alerts from Integration

```http
POST /api/v1/integrations/{integration_id}/sync
Authorization: Bearer <jwt>
```

---

### Service Graph

```http
GET /api/v1/graph
Authorization: Bearer <jwt>
```

Returns nodes and edges suitable for rendering directly with React Flow.

---

### Health Check

```http
GET /api/v1/health
```

Returns `200 OK` with database and Redis connectivity status. No auth required.

```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

---

## 9. WebSocket Events

Connect to `ws://localhost:8000/api/v1/ws?token=<jwt>`.

All messages are JSON with a `type` discriminator field.

### Event Types (Server → Client)

| `type` | Payload | Description |
|---|---|---|
| `connection_established` | `{ "message": "..." }` | Sent on successful handshake |
| `new_alert` | Full `Alert` object | Fired when an alert is ingested |
| `incident_created` | Full `Incident` object | Fired when a new incident is correlated |
| `incident_updated` | Full `Incident` object | Fired on status change or new analysis |
| `analysis_complete` | `{ "incident_id": int, "analysis": {...} }` | Fired when AI analysis finishes |
| `heartbeat` | `{ "timestamp": "..." }` | Sent every 30 seconds |

### Client-side Usage

```typescript
// frontend/src/hooks/useWebSocket.ts
const { isConnected, lastEvent } = useWebSocket();

useEffect(() => {
  if (lastEvent?.type === 'new_alert') {
    setAlerts(prev => [lastEvent.data, ...prev]);
  }
}, [lastEvent]);
```

The `useWebSocket` hook handles authentication, exponential back-off reconnection, and cleanup automatically.

---

## 10. Running Tests

### Backend

Tests use an in-memory SQLite database — no running Docker services needed.

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

Run a specific test file:

```bash
pytest tests/test_correlation_engine.py -v
```

Run with coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

### Frontend

```bash
cd frontend
npm install
npm test
```

Run in watch mode:

```bash
npm test -- --watch
```

---

## 11. Deployment Notes

> The current setup is configured for local development. The following changes are required before a production deployment.

### Must-Do Before Production

- [ ] **Rotate `SECRET_KEY`** — generate a cryptographically secure random value:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] **Change all default passwords** in `.env` (`POSTGRES_PASSWORD`, `FLOWER_PASSWORD`).
- [ ] **Add TLS** — terminate HTTPS/WSS at a reverse proxy (nginx, Caddy, AWS ALB). The app itself has no TLS.
- [ ] **Replace `npm run dev`** with a production build in `frontend/Dockerfile`:
  ```dockerfile
  RUN npm run build
  CMD ["npm", "start"]
  ```
- [ ] **Add rate limiting** on auth endpoints (`/auth/login`, `/auth/signup`).
- [ ] **Add Alembic** for schema migrations — the current `create_all()` approach is not safe for incremental schema changes.
- [ ] **Set `CORS_ORIGINS`** to your actual domain(s).

### Scaling Considerations

- Celery workers are horizontally scalable — add replicas in Compose or Kubernetes.
- The WebSocket manager uses an in-process connection registry; for multi-instance deployments replace it with a Redis pub/sub broadcaster.
- PostgreSQL connection pool is configured via `asyncpg`; tune `pool_size` in `database.py` for high load.

---

## 12. Troubleshooting

### Services fail to start

```bash
# View logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend
```

Make sure Docker Desktop is running and ports 3000, 5432, 6379, 8000, and 5555 are not already in use.

### Backend exits immediately

Check that `.env` exists and is not empty:

```bash
ls -la .env
cat .env
```

If `SECRET_KEY` is missing the backend will refuse to start.

### Frontend shows "Failed to fetch" on the dashboard

This usually means the frontend's server-side requests are going to `localhost:8000` instead of the Docker service name. Verify that `docker-compose.yml` sets `INTERNAL_API_URL=http://backend:8000` in the frontend service environment.

### AI analysis never completes

1. Check that Celery workers are healthy: `docker compose ps celery_worker`
2. Check worker logs: `docker compose logs -f celery_worker`
3. If no `OPENAI_API_KEY` is set, the mock analyzer is used — analysis should still complete within a few seconds.

### Alerts are not being correlated into incidents

The correlation engine groups alerts by overlapping `tags` within a configurable time window. Ensure the alerts you are sending share at least one tag value.

### Database connection errors after schema changes

Because the project uses `create_all()` at startup instead of Alembic, dropping and recreating the volume is the easiest fix during development:

```bash
docker compose down -v   # WARNING: destroys all data
docker compose up --build
```

### Port conflicts

```bash
# Windows
netstat -ano | findstr :8000

# macOS / Linux
lsof -i :8000
```

---

## 13. Roadmap

- [ ] **Alembic migrations** — replace `create_all()` with versioned schema migrations
- [ ] **Rate limiting** — add per-IP and per-user limits on auth and ingestion endpoints
- [ ] **HTTPS support** — bundled nginx config with automatic TLS via Let's Encrypt
- [ ] **Slack / Teams integration** — post incident summaries to chat channels
- [ ] **Webhook outbound** — notify external systems when incident status changes
- [ ] **RBAC** — enforce admin vs. member permissions on write operations
- [ ] **Audit log** — immutable event log for compliance and post-incident review
- [ ] **Alert suppression rules** — silence known-noisy alerts during maintenance windows
- [ ] **Mobile-responsive UI** — current layout targets desktop
- [ ] **Multi-model support** — plug in Anthropic Claude or local LLMs as the analysis backend

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

*Built as a portfolio project demonstrating production-grade full-stack engineering with FastAPI, Next.js 15, async SQLAlchemy, Celery, and OpenAI tool use.*
