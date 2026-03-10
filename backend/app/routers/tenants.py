import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.tenant import Tenant
from app.models.user import User
from app.models.message import Message
from app.models.contact import Contact
from app.schemas.tenant import TenantResponse, TenantUpdate
from app.schemas.user import UserResponse, UserCreate, UserUpdate
from app.services.auth import hash_password

router = APIRouter()


# ---------------------------------------------------------------------------
# Tenant details
# ---------------------------------------------------------------------------

@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the tenant organization for the authenticated user."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.put("/current", response_model=TenantResponse)
async def update_current_tenant(
    body: TenantUpdate,
    user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update tenant name and/or settings. Requires owner or admin role."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.name is not None:
        tenant.name = body.name
    if body.settings is not None:
        # Merge new settings into existing ones
        merged = {**tenant.settings, **body.settings}
        tenant.settings = merged

    await db.commit()
    await db.refresh(tenant)
    return tenant


# ---------------------------------------------------------------------------
# Usage statistics
# ---------------------------------------------------------------------------

@router.get("/current/usage")
async def get_tenant_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return message and contact counts for the current billing period."""
    # Count messages sent this calendar month
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    messages_sent_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.tenant_id == user.tenant_id,
            Message.created_at >= month_start,
        )
    )
    messages_sent = messages_sent_result.scalar() or 0

    contacts_result = await db.execute(
        select(func.count(Contact.id)).where(
            Contact.tenant_id == user.tenant_id,
        )
    )
    contacts_count = contacts_result.scalar() or 0

    # Fetch tenant for credit balance
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    return {
        "messages_sent": messages_sent,
        "contacts": contacts_count,
        "credit_balance": str(tenant.credit_balance) if tenant else "0",
        "plan_tier": tenant.plan_tier if tenant else "free_trial",
        "period_start": month_start.isoformat(),
    }


# ---------------------------------------------------------------------------
# Team member management
# ---------------------------------------------------------------------------

@router.get("/current/users", response_model=list[UserResponse])
async def list_tenant_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """List all users belonging to the current tenant."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(User)
        .where(User.tenant_id == user.tenant_id)
        .order_by(User.created_at)
        .offset(offset)
        .limit(per_page)
    )
    users = result.scalars().all()

    # Fetch the tenant name once for all responses
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    tenant_name = tenant.name if tenant else None

    return [
        UserResponse(
            id=u.id,
            email=u.email,
            first_name=u.first_name,
            last_name=u.last_name,
            role=u.role,
            tenant_id=u.tenant_id,
            tenant_name=tenant_name,
            mfa_enabled=u.mfa_enabled,
            is_active=u.is_active,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post(
    "/current/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_user(
    body: UserCreate,
    user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create (invite) a new user under the current tenant. Requires owner
    or admin role."""
    # Prevent duplicate emails
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Prevent non-owners from creating owner accounts
    if body.role == "owner" and user.role != "owner" and not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can create owner accounts",
        )

    new_user = User(
        tenant_id=user.tenant_id,
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        role=body.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Fetch tenant name
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        role=new_user.role,
        tenant_id=new_user.tenant_id,
        tenant_name=tenant.name if tenant else None,
        mfa_enabled=new_user.mfa_enabled,
        is_active=new_user.is_active,
        last_login_at=new_user.last_login_at,
        created_at=new_user.created_at,
    )


@router.put("/current/users/{user_id}", response_model=UserResponse)
async def update_tenant_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update a team member's profile or role. Requires owner or admin."""
    result = await db.execute(
        select(User).where(
            User.id == user_id, User.tenant_id == user.tenant_id
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent non-owners from promoting to owner
    if (
        body.role == "owner"
        and user.role != "owner"
        and not user.is_superadmin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can assign the owner role",
        )

    if body.first_name is not None:
        target.first_name = body.first_name
    if body.last_name is not None:
        target.last_name = body.last_name
    if body.role is not None:
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active

    await db.commit()
    await db.refresh(target)

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    return UserResponse(
        id=target.id,
        email=target.email,
        first_name=target.first_name,
        last_name=target.last_name,
        role=target.role,
        tenant_id=target.tenant_id,
        tenant_name=tenant.name if tenant else None,
        mfa_enabled=target.mfa_enabled,
        is_active=target.is_active,
        last_login_at=target.last_login_at,
        created_at=target.created_at,
    )


@router.delete(
    "/current/users/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def remove_tenant_user(
    user_id: uuid.UUID,
    user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a team member. Owners cannot be removed by admins."""
    result = await db.execute(
        select(User).where(
            User.id == user_id, User.tenant_id == user.tenant_id
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent removing yourself
    if target.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself",
        )

    # Prevent admins from removing owners
    if target.role == "owner" and user.role != "owner" and not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can remove other owners",
        )

    target.is_active = False
    await db.commit()
    return {"message": "User deactivated", "user_id": str(user_id)}
