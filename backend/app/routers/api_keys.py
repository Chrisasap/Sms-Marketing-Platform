import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.api_key import ApiKey
from app.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas (co-located since they are API-key-specific)
# ---------------------------------------------------------------------------

class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str] = []
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned only at creation time -- includes the full plaintext key."""
    api_key: str


class ApiKeyUpdateRequest(BaseModel):
    name: str | None = None
    scopes: list[str] | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_api_key() -> tuple[str, str, str]:
    """Generate a random API key.

    Returns:
        (plaintext_key, key_prefix, sha256_hash)
    """
    raw = secrets.token_urlsafe(32)
    plaintext = f"bw_{raw}"
    prefix = plaintext[:8]
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    return plaintext, prefix, key_hash


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    body: ApiKeyCreateRequest,
    user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key.  The full plaintext key is returned **once** in
    the response body and must be stored securely by the caller -- it cannot
    be retrieved again."""
    plaintext, prefix, key_hash = _generate_api_key()

    api_key = ApiKey(
        tenant_id=user.tenant_id,
        user_id=user.id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=prefix,
        scopes=body.scopes,
        is_active=True,
        expires_at=body.expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        api_key=plaintext,
    )


@router.get("/", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """List all API keys for the current tenant.  The actual key values are
    never returned -- only the prefix for identification."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.tenant_id == user.tenant_id)
        .order_by(ApiKey.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    keys = result.scalars().all()
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            is_active=k.is_active,
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return metadata for a single API key (no secret)."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id, ApiKey.tenant_id == user.tenant_id
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return key


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: uuid.UUID,
    body: ApiKeyUpdateRequest,
    user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update an API key's name, scopes, or active status."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id, ApiKey.tenant_id == user.tenant_id
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    if body.name is not None:
        key.name = body.name
    if body.scopes is not None:
        key.scopes = body.scopes
    if body.is_active is not None:
        key.is_active = body.is_active

    await db.commit()
    await db.refresh(key)
    return key


@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def revoke_api_key(
    key_id: uuid.UUID,
    user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Permanently revoke (deactivate) an API key."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id, ApiKey.tenant_id == user.tenant_id
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    await db.commit()
    return {"message": "API key revoked", "key_id": str(key_id)}


@router.get("/{key_id}/usage")
async def get_api_key_usage(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return basic usage information for an API key."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id, ApiKey.tenant_id == user.tenant_id
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    return {
        "key_id": str(key.id),
        "name": key.name,
        "is_active": key.is_active,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "created_at": key.created_at.isoformat(),
    }
