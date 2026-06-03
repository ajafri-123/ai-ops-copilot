"""
Tests for authentication endpoints and JWT middleware.

Covers:
  - POST /auth/signup creates org + user + membership, returns JWT
  - POST /auth/signup rejects duplicate email
  - POST /auth/login with valid credentials returns JWT
  - POST /auth/login with wrong password returns 401
  - POST /auth/login with unknown email returns 401
  - GET /auth/me with valid token returns user info
  - GET /auth/me without token returns 401
  - Protected route (GET /alerts) returns 401 without token
  - Protected route returns 200 with valid token
  - Token payload contains user_id and org_id
"""

import pytest
from httpx import AsyncClient

# ─────────────────────────────────────────────
# Fixtures: all tests here use `unauthed_client`
# so real JWT validation runs.
# ─────────────────────────────────────────────

SIGNUP_PAYLOAD = {
    "email": "founder@startup.io",
    "password": "supersecret123",
    "full_name": "Jane Smith",
    "org_name": "Startup Inc",
}


@pytest.mark.asyncio
async def test_signup_returns_token(unauthed_client: AsyncClient):
    response = await unauthed_client.post("/api/v1/auth/signup", json=SIGNUP_PAYLOAD)
    assert response.status_code == 201
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == SIGNUP_PAYLOAD["email"]
    assert isinstance(data["org_id"], int)
    assert isinstance(data["user_id"], int)
    assert data["org_name"] == "Startup Inc"
    assert len(data["access_token"]) > 20


@pytest.mark.asyncio
async def test_signup_duplicate_email_returns_400(unauthed_client: AsyncClient):
    payload = {**SIGNUP_PAYLOAD, "email": "dup@example.com", "org_name": "Org A"}
    await unauthed_client.post("/api/v1/auth/signup", json=payload)

    # Second signup with same email
    resp2 = await unauthed_client.post("/api/v1/auth/signup", json=payload)
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_returns_token(unauthed_client: AsyncClient):
    email = "login_test@example.com"
    payload = {**SIGNUP_PAYLOAD, "email": email, "org_name": "Login Org"}
    await unauthed_client.post("/api/v1/auth/signup", json=payload)

    resp = await unauthed_client.post(
        "/api/v1/auth/login", json={"email": email, "password": SIGNUP_PAYLOAD["password"]}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["email"] == email


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(unauthed_client: AsyncClient):
    email = "wrongpw@example.com"
    await unauthed_client.post(
        "/api/v1/auth/signup",
        json={**SIGNUP_PAYLOAD, "email": email, "org_name": "PW Org"},
    )

    resp = await unauthed_client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert "incorrect" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(unauthed_client: AsyncClient):
    resp = await unauthed_client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@nobody.com", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token_returns_401(unauthed_client: AsyncClient):
    resp = await unauthed_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token(unauthed_client: AsyncClient):
    email = "me_test@example.com"
    signup = await unauthed_client.post(
        "/api/v1/auth/signup",
        json={**SIGNUP_PAYLOAD, "email": email, "org_name": "Me Org"},
    )
    token = signup.json()["access_token"]

    resp = await unauthed_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email
    assert isinstance(data["user_id"], int)
    assert isinstance(data["org_id"], int)


@pytest.mark.asyncio
async def test_protected_route_without_token_returns_401(unauthed_client: AsyncClient):
    """GET /alerts is protected — no token → 401."""
    resp = await unauthed_client.get("/api/v1/alerts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_valid_token_returns_200(unauthed_client: AsyncClient):
    """GET /alerts with a valid token should succeed."""
    email = "alerts_auth@example.com"
    signup = await unauthed_client.post(
        "/api/v1/auth/signup",
        json={**SIGNUP_PAYLOAD, "email": email, "org_name": "Alerts Org"},
    )
    token = signup.json()["access_token"]

    resp = await unauthed_client.get(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_token_contains_expected_claims(unauthed_client: AsyncClient):
    """The JWT payload must contain 'sub' and 'org_id'."""
    import base64
    import json

    email = "claims_test@example.com"
    signup = await unauthed_client.post(
        "/api/v1/auth/signup",
        json={**SIGNUP_PAYLOAD, "email": email, "org_name": "Claims Org"},
    )
    token = signup.json()["access_token"]

    # Decode payload (middle part) without verifying signature
    parts = token.split(".")
    assert len(parts) == 3
    payload_b64 = parts[1] + "=="  # add padding
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))

    assert "sub" in payload
    assert "org_id" in payload
    assert "exp" in payload
    assert isinstance(payload["org_id"], int)


@pytest.mark.asyncio
async def test_org_isolation_alerts(unauthed_client: AsyncClient):
    """Alerts created by org A should not be visible to org B."""
    # Org A
    signup_a = await unauthed_client.post(
        "/api/v1/auth/signup",
        json={**SIGNUP_PAYLOAD, "email": "org_a@test.com", "org_name": "Org Alpha"},
    )
    token_a = signup_a.json()["access_token"]

    # Org B
    signup_b = await unauthed_client.post(
        "/api/v1/auth/signup",
        json={**SIGNUP_PAYLOAD, "email": "org_b@test.com", "org_name": "Org Beta"},
    )
    token_b = signup_b.json()["access_token"]

    from datetime import datetime, timezone
    alert_payload = {
        "source": "aws",
        "severity": "high",
        "title": "Org A secret alert",
        "service_name": "orders-db",
        "environment": "production",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "status": "open",
    }

    # Org A creates an alert
    await unauthed_client.post(
        "/api/v1/alerts",
        json=alert_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Org B lists alerts — should see 0 (different org)
    resp_b = await unauthed_client.get(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.status_code == 200
    org_b_alerts = resp_b.json()["items"]
    assert all(a["title"] != "Org A secret alert" for a in org_b_alerts), (
        "Org isolation violated: Org B can see Org A's alerts"
    )
