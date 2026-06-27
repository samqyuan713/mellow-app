"""
Mellow — Auth Middleware
FastAPI dependencies for route protection.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.utils.security import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency: extract and validate JWT, return current User.
    Use on any protected route.
    """
    payload  = decode_token(credentials.credentials, expected_type="access")
    user_id  = UUID(payload["sub"])

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.subscription)
        )
        .where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    if user.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account has been suspended")

    return user


async def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency: require email-verified user.
    Use on routes that need a verified account.
    """
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address to continue"
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency: require admin role.
    Use on admin-only routes.
    """
    if current_user.role not in ("admin", "moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user


async def get_current_subscription(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> Subscription:
    """
    Dependency: return the user's subscription (creates free one if missing).
    """
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        # Auto-create free subscription for new users
        subscription = Subscription(user_id=current_user.id, plan="free")
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

    return subscription


async def require_premium(
    subscription: Subscription = Depends(get_current_subscription),
) -> Subscription:
    """
    Dependency: require Mellow or Mellow Plus subscription.
    """
    if not subscription.is_premium:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This feature requires a Mellow subscription. Upgrade to unlock."
        )
    return subscription


async def require_plus(
    subscription: Subscription = Depends(get_current_subscription),
) -> Subscription:
    """
    Dependency: require Mellow Plus subscription.
    """
    if not subscription.is_plus:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This feature requires Mellow Plus. Upgrade to unlock."
        )
    return subscription
