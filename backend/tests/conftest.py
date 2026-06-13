"""
pytest fixtures – spins up an in-process SQLite database so tests never need
a live Postgres instance.  Uses the same async path as production.

Auth note
---------
All protected routes require a valid JWT.  In tests we bypass the JWT check by
overriding the `get_auth` FastAPI dependency with a fixed AuthContext.
Tests that specifically exercise the auth endpoints (test_auth.py) use the
`unauthed_client` fixture instead, which only overrides the DB dependency.
"""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import AuthContext, get_auth
from app.core.ratelimit import limiter
from app.main import app

# Per-IP rate limits would 429 the suite (every test shares one client IP)
limiter.enabled = False

# ── Test DB ───────────────────────────────────────────────────────────────────
# StaticPool keeps a single shared connection so the in-memory database
# persists across sessions instead of evaporating per-checkout.

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

# Fixed identity used by the authenticated test client
TEST_ORG_ID: int = 1
TEST_USER_ID: int = 1
TEST_EMAIL: str = "test@example.com"

# Event-loop note: the old hand-rolled session-scoped `event_loop` fixture is
# gone — pytest-asyncio ≥ 0.25 handles loop scoping via the
# `asyncio_default_*_loop_scope` settings in pytest.ini.


# ── Schema setup ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def create_test_tables():
    """Create a fresh schema for every test so tests stay isolated."""
    import app.models  # noqa: F401 – registers models with metadata

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── DB session ────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


# ── HTTP clients ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Authenticated HTTP test client.

    Overrides:
    - get_db  → in-memory SQLite session
    - get_auth → fixed AuthContext (no JWT validation)
    """
    fixed_auth = AuthContext(
        user_id=TEST_USER_ID, org_id=TEST_ORG_ID, email=TEST_EMAIL
    )

    async def override_get_db():
        yield db_session

    async def override_get_auth():
        return fixed_auth

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_auth] = override_get_auth

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthed_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Unauthenticated HTTP test client — used by test_auth.py.

    Only overrides get_db; get_auth is NOT overridden so real JWT validation runs.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
