"""Tests for the /api/v1/auth router endpoints."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.services.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
)
from tests.conftest import (
    TEST_USER_EMAIL,
    TEST_USER_PASSWORD,
    TEST_COMPANY_NAME,
    TEST_TENANT_ID,
    TEST_USER_ID,
    make_test_user,
    make_test_tenant,
)


# ===========================================================================
# Registration
# ===========================================================================


class TestRegisterEndpoint:
    """POST /api/v1/auth/register"""

    @pytest.mark.asyncio
    async def test_register_creates_user_and_tenant(self, client, db_session, override_settings):
        """Successful registration should return 201 with user data."""
        new_user_id = uuid.uuid4()
        new_tenant_id = uuid.uuid4()

        fake_user = MagicMock()
        fake_user.id = new_user_id
        fake_user.email = "newreg@example.com"
        fake_user.first_name = "New"
        fake_user.last_name = "Reg"
        fake_user.role = "owner"
        fake_user.mfa_enabled = False
        fake_user.is_active = True
        fake_user.last_login_at = None
        fake_user.created_at = datetime.now(timezone.utc)

        fake_tenant = MagicMock()
        fake_tenant.id = new_tenant_id
        fake_tenant.name = "New Corp"

        with patch(
            "app.routers.auth.register_user",
            new_callable=AsyncMock,
            return_value=(fake_user, fake_tenant),
        ):
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newreg@example.com",
                    "password": "GoodP@ss123",
                    "first_name": "New",
                    "last_name": "Reg",
                    "company_name": "New Corp",
                },
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newreg@example.com"
        assert data["role"] == "owner"
        assert data["tenant_name"] == "New Corp"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self, client, db_session, override_settings):
        """Registering with an existing email should return 409."""
        with patch(
            "app.routers.auth.register_user",
            new_callable=AsyncMock,
            side_effect=ValueError("Email already registered"),
        ):
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": "AnyP@ss1!",
                    "first_name": "Dup",
                    "last_name": "User",
                    "company_name": "Dup Corp",
                },
            )

        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()


# ===========================================================================
# Login
# ===========================================================================


class TestLoginEndpoint:
    """POST /api/v1/auth/login"""

    @pytest.mark.asyncio
    async def test_login_success_returns_token(self, client, db_session, override_settings):
        """Valid credentials should return an access token and user info."""
        fake_user = make_test_user()

        with patch(
            "app.routers.auth.authenticate_user",
            new_callable=AsyncMock,
            return_value=fake_user,
        ):
            resp = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == TEST_USER_EMAIL
        # Should also set cookies
        cookies = resp.cookies
        # httpx AsyncClient may not expose httponly cookies in all scenarios,
        # but the Set-Cookie header should be present
        assert "set-cookie" in {k.lower() for k in resp.headers.keys()}

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, client, db_session, override_settings):
        """Invalid credentials should return 401."""
        with patch(
            "app.routers.auth.authenticate_user",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": "WrongPassword!",
                },
            )

        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()


# ===========================================================================
# Token refresh
# ===========================================================================


class TestRefreshEndpoint:
    """POST /api/v1/auth/refresh"""

    @pytest.mark.asyncio
    async def test_refresh_token_generates_new_access(self, client, db_session, override_settings):
        """A valid refresh token cookie should yield a new access token."""
        fake_user = make_test_user()
        refresh = create_refresh_token(str(fake_user.id), str(fake_user.tenant_id))

        with patch(
            "app.routers.auth.get_user_by_id",
            new_callable=AsyncMock,
            return_value=fake_user,
        ):
            resp = await client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": refresh},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_without_cookie_returns_401(self, client, db_session, override_settings):
        """Missing refresh token cookie should return 401."""
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401


# ===========================================================================
# Logout
# ===========================================================================


class TestLogoutEndpoint:
    """POST /api/v1/auth/logout"""

    @pytest.mark.asyncio
    async def test_logout_clears_cookies(self, client, override_settings):
        """Logout should return 200 and set cookie deletion headers."""
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Logged out"
        # The response should contain Set-Cookie headers to delete the cookies
        set_cookie_headers = [
            v for k, v in resp.headers.multi_items() if k.lower() == "set-cookie"
        ]
        cookie_names = [h.split("=")[0].strip() for h in set_cookie_headers]
        assert "access_token" in cookie_names
        assert "refresh_token" in cookie_names


# ===========================================================================
# Current user profile
# ===========================================================================


class TestGetMeEndpoint:
    """GET /api/v1/auth/me"""

    @pytest.mark.asyncio
    async def test_get_me_returns_user(self, authenticated_client, db_session, test_user, test_tenant, override_settings):
        """An authenticated request to /me should return the user profile."""
        # The authenticated_client already overrides get_current_user.
        # We need the /me handler to also find the tenant via db.execute.
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_tenant
        db_session.execute = AsyncMock(return_value=mock_result)

        resp = await authenticated_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == test_user.email
        assert data["role"] == test_user.role

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated_returns_401(self, client, override_settings):
        """A request without auth should return 401."""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401 or resp.status_code == 403
