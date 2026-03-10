import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from passlib.hash import argon2
import pyotp
import qrcode
import io
import base64

from app.config import get_settings
from app.models.tenant import Tenant
from app.models.user import User

settings = get_settings()


def hash_password(password: str) -> str:
    return argon2.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return argon2.verify(password, hashed)


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_expire_minutes)
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str, tenant_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_expire_days
    )
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    company_name: str,
) -> tuple[User, Tenant]:
    """Register a new user and create their tenant organization."""
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    # Create tenant with a URL-safe slug
    slug = company_name.lower().replace(" ", "-").replace("'", "")[:50]
    slug_check = await db.execute(select(Tenant).where(Tenant.slug == slug))
    if slug_check.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    tenant = Tenant(
        name=company_name,
        slug=slug,
        plan_tier="free_trial",
        status="active",
        settings={"timezone": "America/New_York"},
    )
    db.add(tenant)
    await db.flush()

    # Create the owner user
    user = User(
        tenant_id=tenant.id,
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role="owner",
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Link tenant back to the owner
    tenant.owner_user_id = user.id
    await db.commit()
    await db.refresh(user)
    await db.refresh(tenant)

    return user, tenant


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """Validate credentials and update last login timestamp."""
    result = await db.execute(
        select(User).where(User.email == email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return user


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def setup_mfa(user_email: str) -> tuple[str, str]:
    """Generate a TOTP secret and QR code data URL for MFA enrollment.

    Returns:
        (secret, qr_code_data_url)
    """
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user_email, issuer_name="BlastWave SMS"
    )

    # Render provisioning URI as a QR code PNG, then base64-encode it
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return secret, f"data:image/png;base64,{qr_b64}"


def verify_mfa(secret: str, code: str) -> bool:
    """Verify a TOTP code against the stored secret."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code)
