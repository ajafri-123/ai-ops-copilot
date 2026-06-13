from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass
class AuthContext:
    user_id: int
    org_id: int
    email: str


async def get_auth(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        org_id = payload.get("org_id")
        if user_id is None or org_id is None:
            raise credentials_exc
    except jwt.InvalidTokenError:
        raise credentials_exc

    from app.models.membership import Membership
    from app.models.user import User

    user = (
        await db.execute(select(User).where(User.id == int(user_id)))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc

    # Re-verify membership: a user removed from the org must lose access
    # immediately, not when their token expires.
    membership = (
        await db.execute(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.org_id == int(org_id),
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise credentials_exc

    return AuthContext(user_id=user.id, org_id=int(org_id), email=user.email)
