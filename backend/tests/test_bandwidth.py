"""Tests for app.services.bandwidth -- Bandwidth V2 API client (mocked HTTP)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.bandwidth import (
    BandwidthClient,
    BandwidthError,
    BandwidthRateLimitError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status_code: int = 200, json_data=None, text: str = "", headers=None):
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text or ""
    resp.headers = headers or {}
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


def _make_client():
    """Create a BandwidthClient with test credentials."""
    return BandwidthClient(
        account_id="test-acct",
        api_token="test-token",
        api_secret="test-secret",
        application_id="test-app-id",
    )


# ===========================================================================
# SMS / MMS sending
# ===========================================================================


class TestSendSMS:
    """Tests for BandwidthClient.send_sms."""

    @pytest.mark.asyncio
    async def test_send_sms_success(self, override_settings):
        """A 200 response from Bandwidth should return the parsed JSON."""
        client = _make_client()
        expected = {"id": "msg-abc", "direction": "out", "text": "Hello"}

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(
            return_value=_make_response(200, expected)
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.send_sms(
                to="+15551234567",
                from_number="+15559876543",
                text="Hello",
            )

        assert result == expected
        mock_http_client.post.assert_awaited_once()
        call_kwargs = mock_http_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["to"] == ["+15551234567"]
        assert payload["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_send_sms_with_tag(self, override_settings):
        """When a tag is provided it should appear in the payload."""
        client = _make_client()
        expected = {"id": "msg-tagged"}

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(
            return_value=_make_response(200, expected)
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.send_sms(
                to="+15551234567",
                from_number="+15559876543",
                text="Tagged",
                tag="campaign-42",
            )

        assert result["id"] == "msg-tagged"
        call_kwargs = mock_http_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["tag"] == "campaign-42"


class TestSendMMS:
    """Tests for BandwidthClient.send_mms."""

    @pytest.mark.asyncio
    async def test_send_mms_success(self, override_settings):
        """MMS should include media URLs in the payload."""
        client = _make_client()
        expected = {"id": "msg-mms", "media": ["https://cdn.example.com/img.jpg"]}

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(
            return_value=_make_response(200, expected)
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.send_mms(
                to="+15551234567",
                from_number="+15559876543",
                text="Check this out",
                media_urls=["https://cdn.example.com/img.jpg"],
            )

        assert result == expected
        call_kwargs = mock_http_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "media" in payload
        assert payload["media"] == ["https://cdn.example.com/img.jpg"]


class TestSendMessageAutoDetect:
    """Tests for BandwidthClient.send_message (auto SMS/MMS detection)."""

    @pytest.mark.asyncio
    async def test_send_message_auto_detects_mms(self, override_settings):
        """Providing media_urls should route to send_mms."""
        client = _make_client()
        client.send_sms = AsyncMock(return_value={"id": "sms"})
        client.send_mms = AsyncMock(return_value={"id": "mms"})

        result = await client.send_message(
            to="+15551234567",
            from_number="+15559876543",
            text="Image attached",
            media_urls=["https://img.example.com/pic.png"],
        )

        assert result == {"id": "mms"}
        client.send_mms.assert_awaited_once()
        client.send_sms.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_message_auto_detects_sms(self, override_settings):
        """No media_urls should route to send_sms."""
        client = _make_client()
        client.send_sms = AsyncMock(return_value={"id": "sms"})
        client.send_mms = AsyncMock(return_value={"id": "mms"})

        result = await client.send_message(
            to="+15551234567",
            from_number="+15559876543",
            text="Just text",
        )

        assert result == {"id": "sms"}
        client.send_sms.assert_awaited_once()
        client.send_mms.assert_not_awaited()


# ===========================================================================
# Error handling
# ===========================================================================


class TestErrorHandling:
    """Tests for HTTP error responses."""

    @pytest.mark.asyncio
    async def test_rate_limit_raises_error(self, override_settings):
        """A 429 response should raise BandwidthRateLimitError."""
        client = _make_client()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(
            return_value=_make_response(429, headers={"Retry-After": "2"})
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        # Disable tenacity retry for this test (would retry 4 times)
        with patch.object(client, "_get_client", return_value=mock_http_client):
            with pytest.raises(BandwidthRateLimitError) as exc_info:
                # Call _request directly to avoid retry decorator complications;
                # use the underlying function
                await client._request.__wrapped__(
                    client, "POST", "https://example.com", json_body={}
                )

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_server_error_raises_bandwidth_error(self, override_settings):
        """A 500 response should raise BandwidthError with status and message."""
        client = _make_client()

        error_json = {"description": "Internal server error", "type": "server-error"}
        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(
            return_value=_make_response(500, json_data=error_json, text="Internal server error")
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            with pytest.raises(BandwidthError) as exc_info:
                await client._request.__wrapped__(
                    client, "POST", "https://example.com", json_body={}
                )

            assert exc_info.value.status_code == 500
            assert "Internal server error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_404_raises_bandwidth_error(self, override_settings):
        """A 404 should raise BandwidthError."""
        client = _make_client()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(
            return_value=_make_response(404, text="Not Found")
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            with pytest.raises(BandwidthError) as exc_info:
                await client._request.__wrapped__(
                    client, "GET", "https://example.com/missing"
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_204_returns_empty_dict(self, override_settings):
        """A 204 No Content should return an empty dict."""
        client = _make_client()

        mock_http_client = AsyncMock()
        mock_http_client.delete = AsyncMock(
            return_value=_make_response(204)
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client._request.__wrapped__(
                client, "DELETE", "https://example.com/resource"
            )
        assert result == {}


# ===========================================================================
# Number management
# ===========================================================================


class TestNumberManagement:
    """Tests for search/order number endpoints."""

    @pytest.mark.asyncio
    async def test_search_numbers(self, override_settings):
        """search_available_numbers should send area code params and return results."""
        client = _make_client()
        response_data = {
            "telephoneNumberList": {
                "telephoneNumber": ["+15551111111", "+15552222222"]
            }
        }

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(
            return_value=_make_response(200, response_data)
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            numbers = await client.search_available_numbers(area_code="555", quantity=2)

        assert len(numbers) == 2
        assert "+15551111111" in numbers

    @pytest.mark.asyncio
    async def test_order_numbers(self, override_settings):
        """order_numbers should POST the number list and site ID."""
        client = _make_client()
        expected = {"orderId": "ord-999", "status": "COMPLETE"}

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(
            return_value=_make_response(200, expected)
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.order_numbers(
                numbers=["+15551111111"],
                site_id="site-1",
            )

        assert result["orderId"] == "ord-999"


# ===========================================================================
# 10DLC / Campaign Registry
# ===========================================================================


class TestCampaignRegistry:
    """Tests for brand/campaign registration."""

    @pytest.mark.asyncio
    async def test_register_brand(self, override_settings):
        """register_brand should POST brand data."""
        client = _make_client()
        expected = {"brandId": "brand-abc", "status": "APPROVED"}

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(
            return_value=_make_response(200, expected)
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.register_brand({"entityName": "Test Corp"})

        assert result["brandId"] == "brand-abc"

    @pytest.mark.asyncio
    async def test_register_campaign(self, override_settings):
        """register_campaign should POST campaign data."""
        client = _make_client()
        expected = {"campaignId": "camp-xyz", "status": "ACTIVE"}

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(
            return_value=_make_response(200, expected)
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            result = await client.register_campaign({"useCase": "MARKETING"})

        assert result["campaignId"] == "camp-xyz"
