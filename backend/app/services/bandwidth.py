"""Bandwidth V2 API client for multi-tenant SMS/MMS platform."""

import httpx
import logging
from typing import Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BandwidthError(Exception):
    """Base exception for Bandwidth API errors."""

    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str | None = None,
    ):
        self.status_code = status_code
        self.message = message
        self.error_code = error_code
        super().__init__(f"Bandwidth API error {status_code}: {message}")


class BandwidthRateLimitError(BandwidthError):
    """Raised when Bandwidth returns HTTP 429."""

    pass


class BandwidthClient:
    """Async Bandwidth V2 API client.

    Covers:
    - Messaging (SMS / MMS send, delivery status)
    - Number management (search, order, release, list)
    - Sub-account management (sites, SIP peers, messaging applications)
    - 10DLC / Campaign Registry (brands, campaigns)
    - Toll-free verification
    """

    MESSAGING_BASE = (
        "https://messaging.bandwidth.com/api/v2/users/{account_id}/messages"
    )
    NUMBERS_BASE = (
        "https://dashboard.bandwidth.com/api/accounts/{account_id}"
    )
    CAMPAIGNS_BASE = (
        "https://dashboard.bandwidth.com/api/accounts/{account_id}"
        "/campaignManagement/10dlc"
    )

    def __init__(
        self,
        account_id: str | None = None,
        api_token: str | None = None,
        api_secret: str | None = None,
        application_id: str | None = None,
    ):
        self.account_id = account_id or settings.bandwidth_account_id
        self.api_token = api_token or settings.bandwidth_api_token
        self.api_secret = api_secret or settings.bandwidth_api_secret
        self.application_id = application_id or settings.bandwidth_application_id
        self._messaging_url = self.MESSAGING_BASE.format(
            account_id=self.account_id
        )
        self._numbers_url = self.NUMBERS_BASE.format(
            account_id=self.account_id
        )
        self._campaigns_url = self.CAMPAIGNS_BASE.format(
            account_id=self.account_id
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Return a fresh async HTTP client with auth and timeouts."""
        return httpx.AsyncClient(
            auth=(self.api_token, self.api_secret),
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"Content-Type": "application/json"},
        )

    @retry(
        retry=retry_if_exception_type(BandwidthRateLimitError),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        url: str,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> dict | list:
        """Make an HTTP request to Bandwidth with automatic retry on 429."""
        async with self._get_client() as client:
            try:
                if method == "POST":
                    resp = await client.post(url, json=json_body)
                elif method == "GET":
                    resp = await client.get(url, params=params)
                elif method == "PUT":
                    resp = await client.put(url, json=json_body)
                elif method == "DELETE":
                    resp = await client.delete(url)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", "1")
                    logger.warning(
                        "Bandwidth rate limited (429), retry-after=%s",
                        retry_after,
                    )
                    raise BandwidthRateLimitError(429, "Rate limited")

                if resp.status_code >= 400:
                    error_body = resp.text
                    error_code: str | None = None
                    try:
                        error_json = resp.json()
                        error_body = error_json.get("description", error_body)
                        error_code = error_json.get("type") or error_json.get(
                            "code"
                        )
                    except Exception:
                        pass
                    raise BandwidthError(
                        resp.status_code, error_body, error_code
                    )

                if resp.status_code == 204:
                    return {}

                return resp.json()

            except httpx.TimeoutException:
                raise BandwidthError(0, "Request timed out")

    # ==================== Messaging API ====================

    async def send_sms(
        self,
        to: str,
        from_number: str,
        text: str,
        tag: str | None = None,
        application_id: str | None = None,
    ) -> dict:
        """Send an SMS message via Bandwidth V2 Messaging."""
        payload: dict[str, Any] = {
            "applicationId": application_id or self.application_id,
            "to": [to],
            "from": from_number,
            "text": text,
        }
        if tag:
            payload["tag"] = tag
        logger.info("Sending SMS to %s from %s", to, from_number)
        return await self._request("POST", self._messaging_url, json_body=payload)

    async def send_mms(
        self,
        to: str,
        from_number: str,
        text: str,
        media_urls: list[str],
        tag: str | None = None,
        application_id: str | None = None,
    ) -> dict:
        """Send an MMS message with media attachments."""
        payload: dict[str, Any] = {
            "applicationId": application_id or self.application_id,
            "to": [to],
            "from": from_number,
            "text": text,
            "media": media_urls,
        }
        if tag:
            payload["tag"] = tag
        logger.info(
            "Sending MMS to %s from %s with %d media",
            to,
            from_number,
            len(media_urls),
        )
        return await self._request("POST", self._messaging_url, json_body=payload)

    async def send_message(
        self,
        to: str,
        from_number: str,
        text: str,
        media_urls: list[str] | None = None,
        tag: str | None = None,
        application_id: str | None = None,
    ) -> dict:
        """Send SMS or MMS depending on whether media is provided."""
        if media_urls:
            return await self.send_mms(
                to, from_number, text, media_urls, tag, application_id
            )
        return await self.send_sms(to, from_number, text, tag, application_id)

    async def get_message_status(self, message_id: str) -> dict:
        """Get delivery status of a message by its Bandwidth message ID."""
        url = f"{self._messaging_url}/{message_id}"
        return await self._request("GET", url)

    # ==================== Number Management ====================

    async def search_available_numbers(
        self,
        area_code: str | None = None,
        state: str | None = None,
        city: str | None = None,
        quantity: int = 10,
        number_type: str = "local",
    ) -> list[dict]:
        """Search for available phone numbers to purchase."""
        url = f"{self._numbers_url}/availableNumbers"
        params: dict[str, Any] = {"quantity": quantity}
        if area_code:
            params["areaCode"] = area_code
        if state:
            params["state"] = state
        if city:
            params["city"] = city
        if number_type == "toll_free":
            url = f"{self._numbers_url}/availableNumbers"
            params["tollFreeWildCardPattern"] = "8**"
        result = await self._request("GET", url, params=params)
        if isinstance(result, list):
            return result
        return (
            result.get("telephoneNumberList", {})
            .get("telephoneNumber", [])
        )

    async def order_numbers(
        self,
        numbers: list[str],
        site_id: str,
        sip_peer_id: str | None = None,
    ) -> dict:
        """Order (purchase) phone numbers on a site."""
        url = f"{self._numbers_url}/orders"
        payload: dict[str, Any] = {
            "existingTelephoneNumberOrderType": {
                "telephoneNumberList": {"telephoneNumber": numbers}
            },
            "siteId": site_id,
        }
        if sip_peer_id:
            payload["sipPeerId"] = sip_peer_id
        logger.info("Ordering %d numbers on site %s", len(numbers), site_id)
        return await self._request("POST", url, json_body=payload)

    async def release_number(self, number: str) -> dict:
        """Disconnect / release a phone number."""
        url = f"{self._numbers_url}/disconnects"
        payload = {
            "disconnectTelephoneNumberOrderType": {
                "telephoneNumberList": {"telephoneNumber": [number]}
            }
        }
        logger.info("Releasing number %s", number)
        return await self._request("POST", url, json_body=payload)

    async def list_numbers(self, site_id: str | None = None) -> list[dict]:
        """List phone numbers on the account, optionally filtered by site."""
        url = f"{self._numbers_url}/tns"
        params: dict[str, Any] = {}
        if site_id:
            params["siteId"] = site_id
        result = await self._request("GET", url, params=params)
        if isinstance(result, list):
            return result
        return result.get("telephoneNumbers", {}).get("telephoneNumber", [])

    async def get_number_details(self, number: str) -> dict:
        """Get detailed info for a single phone number."""
        url = f"{self._numbers_url}/tns/{number}"
        return await self._request("GET", url)

    # ==================== Sub-Account Management ====================

    async def create_site(self, name: str, description: str = "") -> dict:
        """Create a Bandwidth sub-account (Site) for a tenant."""
        url = f"{self._numbers_url}/sites"
        payload = {
            "site": {
                "name": name,
                "description": description,
            }
        }
        logger.info("Creating site: %s", name)
        return await self._request("POST", url, json_body=payload)

    async def get_site(self, site_id: str) -> dict:
        """Get site details."""
        url = f"{self._numbers_url}/sites/{site_id}"
        return await self._request("GET", url)

    async def list_sites(self) -> list[dict]:
        """List all sites on the account."""
        url = f"{self._numbers_url}/sites"
        result = await self._request("GET", url)
        if isinstance(result, list):
            return result
        return result.get("sites", {}).get("site", [])

    async def create_sip_peer(self, site_id: str, name: str) -> dict:
        """Create a Location (SIP Peer) within a Site."""
        url = f"{self._numbers_url}/sites/{site_id}/sippeers"
        payload = {
            "sipPeer": {
                "peerName": name,
                "isDefaultPeer": True,
            }
        }
        logger.info("Creating SIP peer '%s' on site %s", name, site_id)
        return await self._request("POST", url, json_body=payload)

    async def create_messaging_application(
        self,
        name: str,
        callback_url: str,
        inbound_callback_url: str,
    ) -> dict:
        """Create a Messaging Application on the Bandwidth dashboard."""
        url = f"{self._numbers_url}/applications"
        payload = {
            "application": {
                "appName": name,
                "callbackUrl": callback_url,
                "inboundCallbackUrl": inbound_callback_url,
                "msgCallbackUrl": callback_url,
                "requestedCallbackTypes": {
                    "callbackType": [
                        "messaging-delivered",
                        "messaging-failed",
                        "messaging-received",
                    ]
                },
            }
        }
        logger.info("Creating messaging application: %s", name)
        return await self._request("POST", url, json_body=payload)

    async def assign_application_to_location(
        self,
        site_id: str,
        sip_peer_id: str,
        application_id: str,
    ) -> dict:
        """Assign a messaging application to a SIP Peer location."""
        url = (
            f"{self._numbers_url}/sites/{site_id}/sippeers/{sip_peer_id}"
            "/products/messaging/applicationSettings"
        )
        payload = {
            "applicationSettings": {
                "httpMessagingV2AppId": application_id,
            }
        }
        logger.info(
            "Assigning app %s to site %s / peer %s",
            application_id,
            site_id,
            sip_peer_id,
        )
        return await self._request("PUT", url, json_body=payload)

    # ==================== 10DLC / Campaign Registry ====================

    async def register_brand(self, brand_data: dict) -> dict:
        """Register a 10DLC brand with the Campaign Registry via Bandwidth."""
        url = f"{self._campaigns_url}/brands"
        logger.info(
            "Registering 10DLC brand: %s",
            brand_data.get("entityName", "unknown"),
        )
        return await self._request("POST", url, json_body=brand_data)

    async def get_brand(self, brand_id: str) -> dict:
        """Get brand registration status."""
        url = f"{self._campaigns_url}/brands/{brand_id}"
        return await self._request("GET", url)

    async def list_brands(self, page: int = 0, size: int = 50) -> dict:
        """List all registered brands."""
        url = f"{self._campaigns_url}/brands"
        return await self._request(
            "GET", url, params={"page": page, "size": size}
        )

    async def register_campaign(self, campaign_data: dict) -> dict:
        """Register a 10DLC campaign."""
        url = f"{self._campaigns_url}/campaigns"
        logger.info(
            "Registering 10DLC campaign: %s",
            campaign_data.get("useCase", "unknown"),
        )
        return await self._request("POST", url, json_body=campaign_data)

    async def get_campaign(self, campaign_id: str) -> dict:
        """Get campaign registration status."""
        url = f"{self._campaigns_url}/campaigns/{campaign_id}"
        return await self._request("GET", url)

    async def list_campaigns(self, page: int = 0, size: int = 50) -> dict:
        """List all registered 10DLC campaigns."""
        url = f"{self._campaigns_url}/campaigns"
        return await self._request(
            "GET", url, params={"page": page, "size": size}
        )

    # ==================== Toll-Free Verification ====================

    async def submit_toll_free_verification(
        self, number: str, verification_data: dict
    ) -> dict:
        """Submit a toll-free number for verification."""
        url = f"{self._numbers_url}/tollFreeVerification"
        payload = {
            "telephoneNumber": number,
            **verification_data,
        }
        logger.info("Submitting toll-free verification for %s", number)
        return await self._request("POST", url, json_body=payload)

    async def get_toll_free_verification_status(self, number: str) -> dict:
        """Check toll-free verification status."""
        url = f"{self._numbers_url}/tollFreeVerification/{number}"
        return await self._request("GET", url)


# ---------------------------------------------------------------------------
# Singleton instance -- import and use directly
# ---------------------------------------------------------------------------
bandwidth_client = BandwidthClient()
