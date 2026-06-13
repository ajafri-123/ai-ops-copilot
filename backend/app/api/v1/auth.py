"""
Auth endpoints
  POST /api/v1/auth/signup  – create org + user, return JWT
  POST /api/v1/auth/login   – verify credentials, return JWT
  GET  /api/v1/auth/me      – return current user info
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import AuthContext, get_auth
from app.core.ratelimit import AUTH_LOGIN_LIMIT, AUTH_SIGNUP_LIMIT, limiter
from app.core.security import create_access_token, verify_password
from app.crud.user import create_org_and_user, get_user_by_email, get_user_primary_membership
from app.models.organization import Organization
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_SIGNUP_LIMIT)
async def signup(
    request: Request, payload: SignupRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    if await get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already registered")

    user, org, _ = await create_org_and_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        org_name=payload.org_name,
    )

    token = create_access_token({"sub": str(user.id), "org_id": org.id})
    return TokenResponse(
        access_token=token,
        org_id=org.id,
        org_name=org.name,
        user_id=user.id,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(AUTH_LOGIN_LIMIT)
async def login(
    request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    membership = await get_user_primary_membership(db, user.id)
    if not membership:
        raise HTTPException(status_code=400, detail="User has no organization")

    org = (
        await db.execute(select(Organization).where(Organization.id == membership.org_id))
    ).scalar_one()

    token = create_access_token({"sub": str(user.id), "org_id": org.id})
    return TokenResponse(
        access_token=token,
        org_id=org.id,
        org_name=org.name,
        user_id=user.id,
        email=user.email,
    )


@router.get("/me")
async def me(ctx: AuthContext = Depends(get_auth)) -> dict:
    return {"user_id": ctx.user_id, "org_id": ctx.org_id, "email": ctx.email}
