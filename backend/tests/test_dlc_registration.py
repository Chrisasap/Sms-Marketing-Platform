"""Tests for 10DLC assisted registration and admin review queue.

Covers: brand/campaign application submission, validation, review queue
workflow (approve/reject), Bandwidth payload construction, and auth guards.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.services.auth import create_access_token
from tests.conftest import (
    make_test_user,
    make_test_tenant,
    TEST_TENANT_ID,
    TEST_USER_ID,
)


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

VALID_BRAND_DATA = {
    "entity_type": "PRIVATE_PROFIT",
    "legal_name": "Test Corp Inc.",
    "dba_name": "TestCorp",
    "ein": "12-3456789",
    "phone": "+15551234567",
    "email": "support@testcorp.com",
    "street": "123 Main Street",
    "city": "San Francisco",
    "state": "CA",
    "zip_code": "94105",
    "country": "US",
    "website": "https://testcorp.com",
    "vertical": "TECHNOLOGY",
    "brand_relationship": "SMALL_ACCOUNT",
    "is_main": True,
}

VALID_CAMPAIGN_DATA = {
    "brand_id": str(uuid.uuid4()),
    "use_case": "MARKETING",
    "description": "Promotional SMS campaigns for our retail customers about sales and new products.",
    "message_flow": "Customers opt in via our website checkout flow by checking a box that says: I agree to receive marketing SMS from TestCorp.",
    "sample_messages": [
        "Hi {{first_name}}, our spring sale starts tomorrow! Get 20% off with code SPRING20. Reply STOP to opt out."
    ],
    "help_message": "TestCorp SMS Support. For help, call 555-123-4567 or email support@testcorp.com.",
    "optout_message": "You have been unsubscribed from TestCorp messages. Reply START to resubscribe.",
    "subscriber_optin": True,
    "subscriber_optout": True,
    "subscriber_help": True,
    "auto_renewal": True,
}


# ===========================================================================
# Brand Application Submission
# ===========================================================================


class TestBrandApplication:
    """Tests for POST /compliance/brands/apply."""

    @pytest.mark.asyncio
    async def test_submit_brand_application_success(
        self, authenticated_client, db_session
    ):
        """A valid brand application should create Brand + DLCApplication records."""
        # The endpoint calls db.flush, db.commit, and db.refresh on the application.
        # We need refresh to be a no-op (the added objects already have attrs set).
        # Override refresh to copy attributes from the actual ORM object
        async def mock_refresh(obj):
            # DLCApplication objects will have these set by the router code
            if not hasattr(obj, 'id') or obj.id is None:
                obj.id = uuid.uuid4()
            if not hasattr(obj, 'created_at') or obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
        db_session.refresh = AsyncMock(side_effect=mock_refresh)

        resp = await authenticated_client.post(
            "/api/v1/compliance/brands/apply",
            json=VALID_BRAND_DATA,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["application_type"] == "brand"
        assert data["status"] == "pending_review"
        assert data["form_data"]["legal_name"] == "Test Corp Inc."
        # Should have added: Brand10DLC, DLCApplication, AuditLog
        assert db_session.add.call_count >= 3
        db_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_submit_brand_invalid_entity_type(
        self, authenticated_client, db_session
    ):
        """An invalid entity type should return 422."""
        bad_data = {**VALID_BRAND_DATA, "entity_type": "INVALID_TYPE"}
        resp = await authenticated_client.post(
            "/api/v1/compliance/brands/apply",
            json=bad_data,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_brand_invalid_vertical(
        self, authenticated_client, db_session
    ):
        """An invalid vertical should return 422."""
        bad_data = {**VALID_BRAND_DATA, "vertical": "NOT_A_VERTICAL"}
        resp = await authenticated_client.post(
            "/api/v1/compliance/brands/apply",
            json=bad_data,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_brand_invalid_ein(
        self, authenticated_client, db_session
    ):
        """An invalid EIN should return 422."""
        bad_data = {**VALID_BRAND_DATA, "ein": "abc"}
        resp = await authenticated_client.post(
            "/api/v1/compliance/brands/apply",
            json=bad_data,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_brand_missing_required_fields(
        self, authenticated_client, db_session
    ):
        """Missing required fields should return 422."""
        resp = await authenticated_client.post(
            "/api/v1/compliance/brands/apply",
            json={"entity_type": "PRIVATE_PROFIT"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_brand_unauthenticated(self, client):
        """An unauthenticated request should return 401."""
        resp = await client.post(
            "/api/v1/compliance/brands/apply",
            json=VALID_BRAND_DATA,
        )
        assert resp.status_code == 401


# ===========================================================================
# Campaign Application Submission
# ===========================================================================


class TestCampaignApplication:
    """Tests for POST /compliance/campaigns/apply."""

    @pytest.mark.asyncio
    async def test_submit_campaign_application_success(
        self, authenticated_client, db_session
    ):
        """A valid campaign application should create Campaign + DLCApplication."""
        # Mock brand lookup to return a brand owned by the test tenant
        mock_brand = MagicMock()
        mock_brand.id = uuid.UUID(VALID_CAMPAIGN_DATA["brand_id"])
        mock_brand.tenant_id = TEST_TENANT_ID
        mock_brand.bandwidth_brand_id = "bw-brand-123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_brand
        db_session.execute = AsyncMock(return_value=mock_result)

        async def mock_refresh(obj):
            if not hasattr(obj, 'id') or obj.id is None:
                obj.id = uuid.uuid4()
            if not hasattr(obj, 'created_at') or obj.created_at is None:
                obj.created_at = datetime.now(timezone.utc)
        db_session.refresh = AsyncMock(side_effect=mock_refresh)

        resp = await authenticated_client.post(
            "/api/v1/compliance/campaigns/apply",
            json=VALID_CAMPAIGN_DATA,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["application_type"] == "campaign"
        assert data["status"] == "pending_review"

    @pytest.mark.asyncio
    async def test_submit_campaign_brand_not_found(
        self, authenticated_client, db_session
    ):
        """Campaign application for nonexistent brand should return 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)

        resp = await authenticated_client.post(
            "/api/v1/compliance/campaigns/apply",
            json=VALID_CAMPAIGN_DATA,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_campaign_invalid_use_case(
        self, authenticated_client, db_session
    ):
        """An invalid use case should return 422."""
        bad_data = {**VALID_CAMPAIGN_DATA, "use_case": "INVALID_CASE"}
        resp = await authenticated_client.post(
            "/api/v1/compliance/campaigns/apply",
            json=bad_data,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_campaign_description_too_short(
        self, authenticated_client, db_session
    ):
        """Description under 40 chars should return 422."""
        bad_data = {**VALID_CAMPAIGN_DATA, "description": "Too short"}
        resp = await authenticated_client.post(
            "/api/v1/compliance/campaigns/apply",
            json=bad_data,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_campaign_sample_too_short(
        self, authenticated_client, db_session
    ):
        """Sample message under 20 chars should return 422."""
        bad_data = {**VALID_CAMPAIGN_DATA, "sample_messages": ["Too short"]}
        resp = await authenticated_client.post(
            "/api/v1/compliance/campaigns/apply",
            json=bad_data,
        )
        assert resp.status_code == 422


# ===========================================================================
# Tenant Application List
# ===========================================================================


class TestApplicationList:
    """Tests for GET /compliance/applications."""

    @pytest.mark.asyncio
    async def test_list_applications(
        self, authenticated_client, db_session
    ):
        """List applications should return paginated results."""
        # Mock count query and data query
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        db_session.execute = AsyncMock(side_effect=[count_result, data_result])

        resp = await authenticated_client.get("/api/v1/compliance/applications")
        assert resp.status_code == 200
        data = resp.json()
        assert "applications" in data
        assert data["total"] == 0


# ===========================================================================
# Admin Review Queue
# ===========================================================================


class TestAdminDLCQueue:
    """Tests for the superadmin DLC review queue endpoints."""

    @pytest.fixture
    def superadmin_user(self):
        return make_test_user(is_superadmin=True, role="owner")

    @pytest_asyncio.fixture
    async def superadmin_client(self, client, db_session, superadmin_user):
        """Provide an authenticated superadmin client."""
        from app.dependencies import get_current_user, require_superadmin
        from app.main import app

        access_token = create_access_token(
            str(superadmin_user.id),
            str(superadmin_user.tenant_id),
            superadmin_user.role,
        )
        client.headers["Authorization"] = f"Bearer {access_token}"

        async def override_current_user():
            return superadmin_user

        app.dependency_overrides[get_current_user] = override_current_user

        # Override require_superadmin to return a dependency that returns the superadmin
        def override_require_superadmin():
            async def dep():
                return superadmin_user
            return dep

        app.dependency_overrides[require_superadmin()] = override_current_user

        yield client

        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_list_dlc_queue(self, superadmin_client, db_session):
        """GET /admin/dlc-queue should return pending applications."""
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        data_result = MagicMock()
        data_result.scalars.return_value.all.return_value = []

        db_session.execute = AsyncMock(side_effect=[count_result, data_result])

        resp = await superadmin_client.get("/api/v1/admin/dlc-queue")
        assert resp.status_code == 200
        data = resp.json()
        assert "applications" in data

    @pytest.mark.asyncio
    async def test_dlc_queue_requires_superadmin(
        self, authenticated_client, db_session
    ):
        """A regular user should get 403 on the DLC queue."""
        resp = await authenticated_client.get("/api/v1/admin/dlc-queue")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_reject_application(self, superadmin_client, db_session):
        """POST /admin/dlc-queue/{id}/review with reject should set rejection status."""
        app_id = uuid.uuid4()
        mock_app = MagicMock()
        mock_app.id = app_id
        mock_app.status = "pending_review"
        mock_app.tenant_id = TEST_TENANT_ID
        mock_app.application_type = "brand"
        mock_app.brand_id = uuid.uuid4()
        mock_app.campaign_id = None
        mock_app.form_data = VALID_BRAND_DATA
        mock_app.submitted_by = TEST_USER_ID
        mock_app.submitted_at = datetime.now(timezone.utc)
        mock_app.reviewed_by = None
        mock_app.reviewed_at = None
        mock_app.admin_notes = None
        mock_app.rejection_reason = None
        mock_app.bandwidth_response = None
        mock_app.created_at = datetime.now(timezone.utc)

        mock_brand = MagicMock()
        mock_brand.registration_status = "draft"

        # First call: find application, second: find brand
        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = mock_app
        brand_result = MagicMock()
        brand_result.scalar_one_or_none.return_value = mock_brand

        db_session.execute = AsyncMock(side_effect=[app_result, brand_result])

        resp = await superadmin_client.post(
            f"/api/v1/admin/dlc-queue/{app_id}/review",
            json={
                "action": "reject",
                "rejection_reason": "EIN does not match business name",
                "admin_notes": "Please correct and resubmit",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Application rejected"
        assert mock_app.status == "rejected"
        assert mock_app.rejection_reason == "EIN does not match business name"
        assert mock_brand.registration_status == "rejected"

    @pytest.mark.asyncio
    async def test_approve_brand_application(
        self, superadmin_client, db_session, mock_bandwidth
    ):
        """Approving a brand application should submit to Bandwidth API."""
        app_id = uuid.uuid4()
        brand_id = uuid.uuid4()

        mock_app = MagicMock()
        mock_app.id = app_id
        mock_app.status = "pending_review"
        mock_app.tenant_id = TEST_TENANT_ID
        mock_app.application_type = "brand"
        mock_app.brand_id = brand_id
        mock_app.campaign_id = None
        mock_app.form_data = VALID_BRAND_DATA
        mock_app.submitted_by = TEST_USER_ID
        mock_app.submitted_at = datetime.now(timezone.utc)
        mock_app.reviewed_by = None
        mock_app.reviewed_at = None
        mock_app.admin_notes = None
        mock_app.rejection_reason = None
        mock_app.bandwidth_response = None
        mock_app.created_at = datetime.now(timezone.utc)

        mock_brand = MagicMock()
        mock_brand.id = brand_id
        mock_brand.legal_name = "Test Corp Inc."
        mock_brand.dba_name = "TestCorp"
        mock_brand.entity_type = "PRIVATE_PROFIT"
        mock_brand.ein = "12-3456789"
        mock_brand.phone = "+15551234567"
        mock_brand.email = "support@testcorp.com"
        mock_brand.street = "123 Main Street"
        mock_brand.city = "San Francisco"
        mock_brand.state = "CA"
        mock_brand.zip_code = "94105"
        mock_brand.country = "US"
        mock_brand.vertical = "TECHNOLOGY"
        mock_brand.is_main = True
        mock_brand.brand_relationship = "SMALL_ACCOUNT"
        mock_brand.website = "https://testcorp.com"
        mock_brand.stock_symbol = None
        mock_brand.stock_exchange = None
        mock_brand.business_contact_email = None
        mock_brand.alt_business_id = None
        mock_brand.alt_business_id_type = None
        mock_brand.bandwidth_brand_id = None

        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = mock_app
        brand_result = MagicMock()
        brand_result.scalar_one_or_none.return_value = mock_brand

        db_session.execute = AsyncMock(side_effect=[app_result, brand_result])

        # Patch the bandwidth client used in the admin router
        with patch(
            "app.routers.admin.bandwidth_client"
        ) as mock_bw:
            mock_bw.register_brand = AsyncMock(return_value={
                "brandId": "bw-brand-999",
                "identityStatus": "VERIFIED",
            })

            resp = await superadmin_client.post(
                f"/api/v1/admin/dlc-queue/{app_id}/review",
                json={"action": "approve", "admin_notes": "Looks good"},
            )

        assert resp.status_code == 200
        assert mock_app.status == "submitted"
        assert mock_brand.bandwidth_brand_id == "bw-brand-999"
        assert mock_brand.registration_status == "submitted"

    @pytest.mark.asyncio
    async def test_review_non_pending_application(
        self, superadmin_client, db_session
    ):
        """Reviewing an already-reviewed application should return 400."""
        app_id = uuid.uuid4()
        mock_app = MagicMock()
        mock_app.id = app_id
        mock_app.status = "approved"  # Already reviewed

        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = mock_app

        db_session.execute = AsyncMock(return_value=app_result)

        resp = await superadmin_client.post(
            f"/api/v1/admin/dlc-queue/{app_id}/review",
            json={"action": "approve"},
        )
        assert resp.status_code == 400


# ===========================================================================
# Schema Validation
# ===========================================================================


class TestSchemaValidation:
    """Direct schema validation tests."""

    def test_brand_create_valid(self):
        from app.schemas.compliance import BrandCreate
        brand = BrandCreate(**VALID_BRAND_DATA)
        assert brand.entity_type == "PRIVATE_PROFIT"
        assert brand.vertical == "TECHNOLOGY"

    def test_brand_create_invalid_entity(self):
        from app.schemas.compliance import BrandCreate
        with pytest.raises(Exception):
            BrandCreate(**{**VALID_BRAND_DATA, "entity_type": "INVALID"})

    def test_brand_create_invalid_vertical(self):
        from app.schemas.compliance import BrandCreate
        with pytest.raises(Exception):
            BrandCreate(**{**VALID_BRAND_DATA, "vertical": "INVALID"})

    def test_brand_create_invalid_ein(self):
        from app.schemas.compliance import BrandCreate
        with pytest.raises(Exception):
            BrandCreate(**{**VALID_BRAND_DATA, "ein": "abc"})

    def test_campaign_create_valid(self):
        from app.schemas.compliance import CampaignRegistrationCreate
        campaign = CampaignRegistrationCreate(**VALID_CAMPAIGN_DATA)
        assert campaign.use_case == "MARKETING"
        assert campaign.auto_renewal is True

    def test_campaign_create_invalid_use_case(self):
        from app.schemas.compliance import CampaignRegistrationCreate
        with pytest.raises(Exception):
            CampaignRegistrationCreate(**{**VALID_CAMPAIGN_DATA, "use_case": "INVALID"})

    def test_campaign_create_short_description(self):
        from app.schemas.compliance import CampaignRegistrationCreate
        with pytest.raises(Exception):
            CampaignRegistrationCreate(**{**VALID_CAMPAIGN_DATA, "description": "Short"})

    def test_campaign_create_short_sample(self):
        from app.schemas.compliance import CampaignRegistrationCreate
        with pytest.raises(Exception):
            CampaignRegistrationCreate(
                **{**VALID_CAMPAIGN_DATA, "sample_messages": ["Too short"]}
            )

    def test_dlc_review_action_valid(self):
        from app.schemas.compliance import DLCReviewAction
        action = DLCReviewAction(action="approve", admin_notes="OK")
        assert action.action == "approve"

    def test_dlc_review_action_invalid(self):
        from app.schemas.compliance import DLCReviewAction
        with pytest.raises(Exception):
            DLCReviewAction(action="invalid_action")

    def test_all_entity_types(self):
        from app.schemas.compliance import ENTITY_TYPES
        assert len(ENTITY_TYPES) == 5
        assert "PRIVATE_PROFIT" in ENTITY_TYPES
        assert "SOLE_PROPRIETOR" in ENTITY_TYPES

    def test_all_use_cases(self):
        from app.schemas.compliance import USE_CASES
        assert "MARKETING" in USE_CASES
        assert "2FA" in USE_CASES
        assert "MIXED" in USE_CASES
        assert len(USE_CASES) >= 13

    def test_all_verticals(self):
        from app.schemas.compliance import VERTICALS
        assert "TECHNOLOGY" in VERTICALS
        assert "HEALTHCARE" in VERTICALS
        assert len(VERTICALS) >= 20
