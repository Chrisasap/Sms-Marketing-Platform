import uuid
import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.database import get_db
from app.services.auth import (
    register_user,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    setup_mfa,
    verify_mfa,
    hash_password,
    get_user_by_id,
)
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    TokenRefreshResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    MFASetupResponse,
    MFAVerifyRequest,
    MFALoginRequest,
)
from app.schemas.user import UserResponse
from app.dependencies import get_current_user
from app.models.user import User
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Simple in-memory rate limiter
# ---------------------------------------------------------------------------

_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(key: str, max_attempts: int, window_seconds: int) -> bool:
    """Return True if the request is within rate limits, False if exceeded."""
    now = time.time()
    cutoff = now - window_seconds
    # Prune expired entries
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if t > cutoff]
    if len(_rate_limit_store[key]) >= max_attempts:
        return False
    _rate_limit_store[key].append(now)
    return True


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, checking common proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and create a tenant organization."""
    # Rate limit: max 3 per IP per hour
    client_ip = _get_client_ip(request)
    if not _check_rate_limit(f"register:{client_ip}", max_attempts=3, window_seconds=3600):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Try again later.",
        )

    try:
        user, tenant = await register_user(
            db,
            req.email,
            req.password,
            req.first_name,
            req.last_name,
            req.company_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        mfa_enabled=user.mfa_enabled,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# Login / Logout / Refresh
# ---------------------------------------------------------------------------

@router.post("/login")
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email + password. Returns JWT tokens in both the
    response body and httpOnly cookies.

    If the user has MFA enabled, returns a partial response with
    ``mfa_required: true`` and a short-lived ``mfa_token`` instead of
    full auth tokens. The client must then call ``/auth/mfa/validate``.
    """
    # Rate limit: max 5 per IP per minute
    client_ip = _get_client_ip(request)
    if not _check_rate_limit(f"login:{client_ip}", max_attempts=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )

    user = await authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # If MFA is enabled, return a partial response requiring TOTP validation
    if user.mfa_enabled:
        mfa_token = create_access_token(
            str(user.id),
            str(user.tenant_id),
            user.role,
            expires_delta=timedelta(minutes=5),
        )
        # Override the token type to "mfa_pending" so it cannot be used as
        # a regular access token.
        from jose import jwt as jose_jwt
        from app.config import get_settings
        settings = get_settings()
        payload = jose_jwt.decode(
            mfa_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        payload["type"] = "mfa_pending"
        mfa_token = jose_jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        return {
            "mfa_required": True,
            "mfa_token": mfa_token,
        }

    access_token = create_access_token(
        str(user.id), str(user.tenant_id), user.role
    )
    refresh_token = create_refresh_token(str(user.id), str(user.tenant_id))

    # Set httpOnly cookies so the browser can authenticate transparently
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=900,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=604800,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "tenant_id": str(user.tenant_id),
        },
    }


# ---------------------------------------------------------------------------
# MFA login validation
# ---------------------------------------------------------------------------

@router.post("/mfa/validate")
async def mfa_validate(
    req: MFALoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Validate a TOTP code after login when MFA is enabled.

    Accepts the short-lived ``mfa_token`` from the login response plus
    the user's TOTP ``code``.  On success, issues full auth tokens.
    """
    try:
        payload = decode_token(req.mfa_token)
        if payload.get("type") != "mfa_pending":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA token",
            )
        user = await get_user_by_id(db, uuid.UUID(payload["sub"]))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        )

    if not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not configured for this user",
        )

    if not verify_mfa(user.mfa_secret, req.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    access_token = create_access_token(
        str(user.id), str(user.tenant_id), user.role
    )
    refresh_token = create_refresh_token(str(user.id), str(user.tenant_id))

    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=900,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=604800,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "tenant_id": str(user.tenant_id),
        },
    }


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a new access token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user = await get_user_by_id(db, uuid.UUID(payload["sub"]))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    new_access = create_access_token(
        str(user.id), str(user.tenant_id), user.role
    )
    response.set_cookie(
        "access_token",
        new_access,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=900,
    )
    return TokenRefreshResponse(access_token=new_access)


@router.post("/logout")
async def logout(response: Response):
    """Clear authentication cookies."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


# ---------------------------------------------------------------------------
# Current user profile
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's profile, including tenant name."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=tenant.name if tenant else None,
        mfa_enabled=user.mfa_enabled,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# Multi-factor authentication
# ---------------------------------------------------------------------------

@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a TOTP secret and QR code for the current user."""
    secret, qr_url = setup_mfa(user.email)
    user.mfa_secret = secret
    await db.commit()
    return MFASetupResponse(secret=secret, qr_code_url=qr_url)


@router.post("/mfa/verify")
async def mfa_verify(
    req: MFAVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a TOTP code and permanently enable MFA for the user."""
    if not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not set up")
    if not verify_mfa(user.mfa_secret, req.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    user.mfa_enabled = True
    await db.commit()
    return {"message": "MFA enabled successfully"}


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@router.post("/password-reset/request")
async def request_password_reset(
    req: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Initiate a password-reset flow.  Always returns success to prevent
    email enumeration attacks."""
    # Rate limit: max 5 per IP per minute
    client_ip = _get_client_ip(request)
    if not _check_rate_limit(f"password_reset:{client_ip}", max_attempts=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset attempts. Try again later.",
        )

    # Look up user by email
    result = await db.execute(
        select(User).where(User.email == req.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user:
        # Generate a short-lived password-reset JWT (15 minutes)
        from jose import jwt as jose_jwt
        from app.config import get_settings
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        reset_payload = {
            "sub": str(user.id),
            "exp": expire,
            "type": "password_reset",
        }
        reset_token = jose_jwt.encode(
            reset_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        # In production this would dispatch an email via a background task.
        logger.info(
            "Password reset token generated for %s: %s",
            req.email,
            reset_token,
        )

    return {"message": "If an account exists, a reset email has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    req: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Consume a password-reset token and update the user's password."""
    try:
        payload = decode_token(req.token)
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=400, detail="Invalid reset token"
            )
        user = await get_user_by_id(db, uuid.UUID(payload["sub"]))
        if not user:
            raise HTTPException(
                status_code=400, detail="Invalid reset token"
            )
        user.password_hash = hash_password(req.new_password)
        await db.commit()
        return {"message": "Password reset successful"}
    except JWTError:
        raise HTTPException(
            status_code=400, detail="Invalid or expired reset token"
        )
