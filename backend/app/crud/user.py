import re
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.membership import Membership, MemberRole
from app.models.organization import Organization
from app.models.user import User


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:100] or "org"


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    # Emails are stored lowercased; normalise lookups the same way so
    # Foo@x.com and foo@x.com can never become two accounts.
    return (
        await db.execute(select(User).where(User.email == email.strip().lower()))
    ).scalar_one_or_none()


async def create_org_and_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str | None,
    org_name: str,
) -> tuple[User, Organization, Membership]:
    base_slug = _slugify(org_name)
    slug, counter = base_slug, 1
    while (
        await db.execute(select(Organization).where(Organization.slug == slug))
    ).scalar_one_or_none():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(name=org_name, slug=slug)
    db.add(org)
    try:
        await db.flush()
    except IntegrityError:
        # Lost the slug race against a concurrent signup — retry once with a
        # short random suffix so two orgs of the same name don't 500.
        await db.rollback()
        org = Organization(name=org_name, slug=f"{base_slug[:90]}-{secrets.token_hex(4)}")
        db.add(org)
        await db.flush()

    user = User(
        email=email.strip().lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.flush()

    membership = Membership(user_id=user.id, org_id=org.id, role=MemberRole.owner)
    db.add(membership)
    await db.commit()
    await db.refresh(user)
    await db.refresh(org)
    await db.refresh(membership)

    return user, org, membership


async def get_user_primary_membership(db: AsyncSession, user_id: int) -> Membership | None:
    # first() rather than scalar_one_or_none(): a user with multiple
    # memberships must not turn login into a 500.
    return (
        await db.execute(
            select(Membership)
            .where(Membership.user_id == user_id)
            .order_by(Membership.id)
        )
    ).scalars().first()
