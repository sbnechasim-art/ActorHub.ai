"""
ActorHub Python SDK Client

Main client for interacting with the ActorHub.ai API.
Supports both sync and async operations.
"""
import httpx
from typing import Optional, Union
import base64

from actorhub.models import (
    VerifyResponse,
    VerifyResult,
    License,
    PriceBreakdown,
    LicenseType,
    UsageType,
)
from actorhub.exceptions import (
    ActorHubError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
)


class ActorHub:
    """
    Synchronous client for ActorHub.ai API.

    Usage:
        client = ActorHub(api_key="your_api_key")
        result = client.verify(image_url="https://example.com/face.jpg")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.actorhub.ai/v1",
        timeout: float = 30.0,
    ):
        """
        Initialize the ActorHub client.

        Args:
            api_key: Your ActorHub API key
            base_url: API base URL (default: production)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-API-Key": api_key,
                "User-Agent": "ActorHub-Python-SDK/1.0.0",
            },
            timeout=timeout,
        )

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise appropriate exceptions"""
        if response.status_code == 200:
            return response.json()

        error_data = response.json() if response.content else {}
        message = error_data.get("detail", error_data.get("message", "Unknown error"))

        if response.status_code == 401:
            raise AuthenticationError(message)
        elif response.status_code == 404:
            raise NotFoundError(message)
        elif response.status_code == 400:
            raise ValidationError(message)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(message, retry_after=int(retry_after) if retry_after else None)
        else:
            raise ActorHubError(message, status_code=response.status_code, response=error_data)

    def verify(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        include_license_options: bool = True,
    ) -> VerifyResponse:
        """
        Check if an image contains protected identities.

        This is the core API call for checking faces before AI generation.

        Args:
            image_url: URL of image to check
            image_base64: Base64 encoded image
            image_bytes: Raw image bytes
            include_license_options: Include licensing options in response

        Returns:
            VerifyResponse with protection status and identity details

        Raises:
            ValidationError: If no image source provided
            AuthenticationError: If API key is invalid
        """
        payload = {"include_license_options": include_license_options}

        if image_url:
            payload["image_url"] = image_url
        elif image_base64:
            payload["image_base64"] = image_base64
        elif image_bytes:
            payload["image_base64"] = base64.b64encode(image_bytes).decode()
        else:
            raise ValidationError("Must provide image_url, image_base64, or image_bytes")

        response = self._client.post("/identity/verify", json=payload)
        data = self._handle_response(response)

        return VerifyResponse(
            protected=data["protected"],
            faces_detected=data["faces_detected"],
            identities=[VerifyResult(**i) for i in data.get("identities", [])],
            message=data.get("message", ""),
            response_time_ms=data.get("response_time_ms", 0),
            request_id=data.get("request_id", ""),
        )

    def get_license_price(
        self,
        identity_id: str,
        license_type: Union[LicenseType, str],
        usage_type: Union[UsageType, str],
        duration_days: int = 30,
    ) -> PriceBreakdown:
        """
        Get pricing for a license.

        Args:
            identity_id: ID of the identity to license
            license_type: Type of license (single_use, subscription, unlimited)
            usage_type: Usage type (commercial, personal, editorial)
            duration_days: License duration in days

        Returns:
            PriceBreakdown with pricing details
        """
        response = self._client.post(
            "/marketplace/license/price",
            json={
                "identity_id": identity_id,
                "license_type": str(license_type),
                "usage_type": str(usage_type),
                "duration_days": duration_days,
            },
        )
        data = self._handle_response(response)
        return PriceBreakdown(**data)

    def purchase_license(
        self,
        identity_id: str,
        license_type: Union[LicenseType, str],
        usage_type: Union[UsageType, str],
        duration_days: int = 30,
        project_name: Optional[str] = None,
        project_description: Optional[str] = None,
    ) -> dict:
        """
        Purchase a license for using a protected identity.

        Args:
            identity_id: ID of the identity to license
            license_type: Type of license
            usage_type: How the identity will be used
            duration_days: License duration
            project_name: Name of your project
            project_description: Description of how you'll use the identity

        Returns:
            Dict with checkout_url for payment and license details
        """
        response = self._client.post(
            "/marketplace/license/purchase",
            json={
                "identity_id": identity_id,
                "license_type": str(license_type),
                "usage_type": str(usage_type),
                "duration_days": duration_days,
                "project_name": project_name,
                "project_description": project_description,
            },
        )
        return self._handle_response(response)

    def download_actor_pack(
        self,
        identity_id: str,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Download Actor Pack for a licensed identity.

        Args:
            identity_id: ID of the identity
            output_path: Path to save the downloaded pack

        Returns:
            Path to downloaded file
        """
        # Get download URL
        response = self._client.get(f"/actor-pack/download/{identity_id}")
        data = self._handle_response(response)

        download_url = data["download_url"]

        # Download file
        if output_path is None:
            output_path = f"actor_pack_{identity_id}.zip"

        with httpx.stream("GET", download_url) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)

        return output_path

    def get_my_licenses(self, active_only: bool = False) -> list:
        """Get all licenses for the current user"""
        response = self._client.get(
            "/marketplace/licenses/mine",
            params={"active_only": active_only},
        )
        return self._handle_response(response)

    def close(self):
        """Close the HTTP client"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AsyncActorHub:
    """
    Asynchronous client for ActorHub.ai API.

    Usage:
        async with AsyncActorHub(api_key="your_api_key") as client:
            result = await client.verify(image_url="https://example.com/face.jpg")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.actorhub.ai/v1",
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "X-API-Key": api_key,
                "User-Agent": "ActorHub-Python-SDK/1.0.0",
            },
            timeout=timeout,
        )

    async def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise appropriate exceptions"""
        if response.status_code == 200:
            return response.json()

        error_data = response.json() if response.content else {}
        message = error_data.get("detail", error_data.get("message", "Unknown error"))

        if response.status_code == 401:
            raise AuthenticationError(message)
        elif response.status_code == 404:
            raise NotFoundError(message)
        elif response.status_code == 400:
            raise ValidationError(message)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(message, retry_after=int(retry_after) if retry_after else None)
        else:
            raise ActorHubError(message, status_code=response.status_code, response=error_data)

    async def verify(
        self,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        include_license_options: bool = True,
    ) -> VerifyResponse:
        """Async version of verify"""
        payload = {"include_license_options": include_license_options}

        if image_url:
            payload["image_url"] = image_url
        elif image_base64:
            payload["image_base64"] = image_base64
        elif image_bytes:
            payload["image_base64"] = base64.b64encode(image_bytes).decode()
        else:
            raise ValidationError("Must provide image_url, image_base64, or image_bytes")

        response = await self._client.post("/identity/verify", json=payload)
        data = await self._handle_response(response)

        return VerifyResponse(
            protected=data["protected"],
            faces_detected=data["faces_detected"],
            identities=[VerifyResult(**i) for i in data.get("identities", [])],
            message=data.get("message", ""),
            response_time_ms=data.get("response_time_ms", 0),
            request_id=data.get("request_id", ""),
        )

    async def get_license_price(
        self,
        identity_id: str,
        license_type: Union[LicenseType, str],
        usage_type: Union[UsageType, str],
        duration_days: int = 30,
    ) -> PriceBreakdown:
        """Async version of get_license_price"""
        response = await self._client.post(
            "/marketplace/license/price",
            json={
                "identity_id": identity_id,
                "license_type": str(license_type),
                "usage_type": str(usage_type),
                "duration_days": duration_days,
            },
        )
        data = await self._handle_response(response)
        return PriceBreakdown(**data)

    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
