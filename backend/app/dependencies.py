import uuid

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from app.database import get_db
from app.services.auth import decode_token, get_user_by_id
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    """Extract and validate the JWT from either the Authorization header
    (Bearer token) or the ``access_token`` cookie.  Returns the authenticated
    :class:`User` and populates ``request.state`` with tenant context.
    """
    token = None

    # Prefer Authorization header
    if credentials:
        token = credentials.credentials

    # Fall back to httpOnly cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Attach tenant context so downstream code can use it without re-querying
    request.state.tenant_id = user.tenant_id
    request.state.user_id = user.id
    request.state.user_role = user.role

    return user


def require_role(*roles: str):
    """Dependency factory -- ensures the authenticated user holds one of the
    given roles.  Superadmins bypass the check entirely."""

    async def check_role(user: User = Depends(get_current_user)) -> User:
        if user.is_superadmin:
            return user
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return user

    return check_role


async def get_tenant_id(user: User = Depends(get_current_user)) -> uuid.UUID:
    """Convenience dependency that yields just the tenant UUID."""
    return user.tenant_id


def require_superadmin():
    """Dependency factory that restricts access to superadmin users."""

    async def check(user: User = Depends(get_current_user)) -> User:
        if not user.is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin access required",
            )
        return user

    return check
