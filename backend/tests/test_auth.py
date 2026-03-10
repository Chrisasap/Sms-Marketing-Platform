"""Tests for app.services.auth -- password hashing, JWT tokens, MFA, user registration."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pyotp
from jose import jwt, JWTError

from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    register_user,
    authenticate_user,
    setup_mfa,
    verify_mfa,
)
from tests.conftest import (
    TEST_JWT_SECRET,
    TEST_JWT_ALGORITHM,
    TEST_USER_EMAIL,
    TEST_USER_PASSWORD,
    TEST_TENANT_ID,
    TEST_USER_ID,
    make_test_user,
)


# ===========================================================================
# Password hashing
# ===========================================================================


class TestPasswordHashing:
    """Tests for hash_password / verify_password using argon2."""

    def test_hash_and_verify_password(self, override_settings):
        """A hashed password should verify against the original plaintext."""
        hashed = hash_password("MyP@ssword123")
        assert hashed != "MyP@ssword123"
        assert hashed.startswith("$argon2")
        assert verify_password("MyP@ssword123", hashed) is True

    def test_verify_wrong_password(self, override_settings):
        """A wrong plaintext should fail verification."""
        hashed = hash_password("CorrectPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_hash_produces_unique_values(self, override_settings):
        """Two calls with the same input should produce different hashes (random salt)."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts

    def test_empty_password_hashes(self, override_settings):
        """Even an empty string can be hashed and verified."""
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False


# ===========================================================================
# JWT access tokens
# ===========================================================================


class TestAccessToken:
    """Tests for create_access_token / decode_token."""

    def test_create_and_decode_access_token(self, override_settings):
        """A freshly created access token should decode to the correct claims."""
        user_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        token = create_access_token(user_id, tenant_id, "owner")

        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["tenant_id"] == tenant_id
        assert payload["role"] == "owner"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_access_token_custom_expiry(self, override_settings):
        """A custom expiry delta should be respected."""
        token = create_access_token(
            "uid", "tid", "sender",
            expires_delta=timedelta(minutes=5),
        )
        payload = decode_token(token)
        # The expiry should be approximately 5 minutes from now (within 10 s tolerance)
        exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected = datetime.now(timezone.utc) + timedelta(minutes=5)
        assert abs((exp_dt - expected).total_seconds()) < 10

    def test_decode_token_expired(self, override_settings):
        """An expired token should raise JWTError on decode."""
        token = create_access_token(
            "uid", "tid", "owner",
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(Exception):
            # jose raises ExpiredSignatureError (subclass of JWTError)
            decode_token(token)

    def test_decode_token_invalid(self, override_settings):
        """A garbage string should raise on decode."""
        with pytest.raises(Exception):
            decode_token("not.a.valid.token")

    def test_decode_token_wrong_secret(self, override_settings):
        """A token signed with a different secret should fail."""
        token = jwt.encode(
            {"sub": "x", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "wrong-secret",
            algorithm="HS256",
        )
        with pytest.raises(Exception):
            decode_token(token)


# ===========================================================================
# JWT refresh tokens
# ===========================================================================


class TestRefreshToken:
    """Tests for create_refresh_token."""

    def test_create_and_decode_refresh_token(self, override_settings):
        """A refresh token should decode with type='refresh'."""
        user_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        token = create_refresh_token(user_id, tenant_id)

        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["tenant_id"] == tenant_id
        assert payload["type"] == "refresh"
        assert "exp" in payload

    def test_refresh_token_has_long_expiry(self, override_settings):
        """Refresh tokens should expire days in the future, not minutes."""
        token = create_refresh_token("uid", "tid")
        payload = decode_token(token)
        exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        # Should be at least 6 days from now (default is 7)
        assert (exp_dt - datetime.now(timezone.utc)).days >= 6


# ===========================================================================
# User registration
# ===========================================================================


class TestRegisterUser:
    """Tests for register_user (async, needs mocked DB)."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, db_session, override_settings):
        """Registering a new user should create both a Tenant and a User."""
        # register_user calls db.execute twice before creating objects:
        # 1. Check if email exists -> None
        # 2. Check if slug exists -> None
        # We cannot patch User/Tenant classes because SQLAlchemy's select()
        # needs the real ORM models.  Instead we let the constructors run and
        # just verify the side effects on the mock session.
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        user, tenant = await register_user(
            db_session,
            email="new@example.com",
            password="StrongP@ss1",
            first_name="Alice",
            last_name="Smith",
            company_name="Alice Corp",
        )

        # Verify the returned objects have the expected attributes
        assert user.email == "new@example.com"
        assert user.first_name == "Alice"
        assert user.last_name == "Smith"
        assert user.role == "owner"
        assert tenant.name == "Alice Corp"
        assert tenant.plan_tier == "free_trial"
        assert tenant.slug.startswith("alice-corp")
        # Verify both were added to the session
        assert db_session.add.call_count >= 2
        db_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, db_session, override_settings):
        """Registering with an existing email should raise ValueError."""
        existing_user = make_test_user()

        # First execute call (email check) returns a user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        db_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Email already registered"):
            await register_user(
                db_session,
                email=TEST_USER_EMAIL,
                password="AnyPass1!",
                first_name="Dup",
                last_name="User",
                company_name="Dup Corp",
            )


# ===========================================================================
# User authentication
# ===========================================================================


class TestAuthenticateUser:
    """Tests for authenticate_user (async)."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, db_session, override_settings):
        """Valid credentials should return the user and update last_login_at."""
        user = make_test_user()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await authenticate_user(db_session, TEST_USER_EMAIL, TEST_USER_PASSWORD)
        assert result is user
        db_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, db_session, override_settings):
        """Wrong password should return None."""
        user = make_test_user()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await authenticate_user(db_session, TEST_USER_EMAIL, "WrongPassword!")
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent(self, db_session, override_settings):
        """A non-existent email should return None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        result = await authenticate_user(db_session, "ghost@example.com", "anything")
        assert result is None


# ===========================================================================
# MFA
# ===========================================================================


class TestMFA:
    """Tests for setup_mfa / verify_mfa."""

    def test_mfa_setup_and_verify(self, override_settings):
        """Setting up MFA should return a secret and QR URL; the secret should produce valid codes."""
        secret, qr_url = setup_mfa("user@example.com")

        assert isinstance(secret, str)
        assert len(secret) > 10
        assert qr_url.startswith("data:image/png;base64,")

        # Generate a valid TOTP code from the secret
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_mfa(secret, code) is True

    def test_mfa_verify_wrong_code(self, override_settings):
        """A wrong TOTP code should fail verification."""
        secret, _ = setup_mfa("user@example.com")
        assert verify_mfa(secret, "000000") is False

    def test_mfa_verify_empty_code(self, override_settings):
        """An empty code should fail verification."""
        secret, _ = setup_mfa("user@example.com")
        assert verify_mfa(secret, "") is False

    def test_mfa_setup_generates_unique_secrets(self, override_settings):
        """Each call to setup_mfa should produce a different secret."""
        s1, _ = setup_mfa("a@example.com")
        s2, _ = setup_mfa("b@example.com")
        assert s1 != s2
