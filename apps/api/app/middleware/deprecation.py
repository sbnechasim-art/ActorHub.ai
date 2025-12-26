"""
Deprecation Middleware

Adds deprecation and sunset headers to deprecated endpoints.
This helps clients prepare for API changes before they happen.

Headers added:
- Deprecation: <date> - When the endpoint was deprecated
- Sunset: <date> - When the endpoint will be removed
- Link: <url>; rel="successor-version" - New endpoint URL
- X-API-Version: <version> - Current API version
"""

from datetime import datetime, timezone
from typing import Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# API Version
API_VERSION = "1.1"

# Deprecated endpoints with their deprecation info
# Format: path -> {deprecated_date, sunset_date, successor_url, message}
DEPRECATED_ENDPOINTS: Dict[str, dict] = {
    # Example entries - add actual deprecated endpoints here
    # "/api/v1/license/price": {
    #     "deprecated": "2025-01-01",
    #     "sunset": "2025-06-01",
    #     "successor": "/api/v1/licenses/pricing",
    #     "message": "Use GET /api/v1/licenses/pricing instead"
    # },
}

# Legacy parameter mappings (old param -> new param)
DEPRECATED_PARAMS: Dict[str, Dict[str, str]] = {
    "skip": {
        "replacement": "page",
        "message": "Parameter 'skip' is deprecated. Use 'page' for pagination.",
    }
}


class DeprecationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds deprecation headers to responses.

    Usage:
        app.add_middleware(DeprecationMiddleware)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Always add API version header
        response.headers["X-API-Version"] = API_VERSION

        # Add request ID if not present
        request_id = request.headers.get("X-Request-ID")
        if request_id:
            response.headers["X-Request-ID"] = request_id

        # Check for deprecated endpoints
        path = request.url.path
        if path in DEPRECATED_ENDPOINTS:
            deprecation_info = DEPRECATED_ENDPOINTS[path]
            self._add_deprecation_headers(response, deprecation_info)

        # Check for deprecated parameters
        query_params = dict(request.query_params)
        for param, info in DEPRECATED_PARAMS.items():
            if param in query_params:
                # Add warning header for deprecated params
                existing_warning = response.headers.get("Warning", "")
                warning = f'299 - "{info["message"]}"'
                if existing_warning:
                    response.headers["Warning"] = f"{existing_warning}, {warning}"
                else:
                    response.headers["Warning"] = warning

        return response

    def _add_deprecation_headers(
        self,
        response: Response,
        info: dict
    ) -> None:
        """Add RFC 8594 deprecation headers to response."""

        # Deprecation header (RFC 8594)
        if "deprecated" in info:
            response.headers["Deprecation"] = info["deprecated"]

        # Sunset header (RFC 8594)
        if "sunset" in info:
            response.headers["Sunset"] = info["sunset"]

        # Link header pointing to successor
        if "successor" in info:
            response.headers["Link"] = f'<{info["successor"]}>; rel="successor-version"'


def add_deprecation(
    path: str,
    deprecated_date: str,
    sunset_date: str,
    successor_url: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    """
    Register a deprecated endpoint.

    Args:
        path: The endpoint path (e.g., "/api/v1/old-endpoint")
        deprecated_date: ISO date when deprecated (e.g., "2025-01-01")
        sunset_date: ISO date when it will be removed
        successor_url: URL of the replacement endpoint
        message: Human-readable deprecation message

    Example:
        add_deprecation(
            path="/api/v1/license/price",
            deprecated_date="2025-01-01",
            sunset_date="2025-06-01",
            successor_url="/api/v1/licenses/pricing",
            message="Use GET /api/v1/licenses/pricing instead"
        )
    """
    DEPRECATED_ENDPOINTS[path] = {
        "deprecated": deprecated_date,
        "sunset": sunset_date,
    }
    if successor_url:
        DEPRECATED_ENDPOINTS[path]["successor"] = successor_url
    if message:
        DEPRECATED_ENDPOINTS[path]["message"] = message


def is_deprecated(path: str) -> bool:
    """Check if an endpoint is deprecated."""
    return path in DEPRECATED_ENDPOINTS


def get_deprecation_info(path: str) -> Optional[dict]:
    """Get deprecation info for an endpoint."""
    return DEPRECATED_ENDPOINTS.get(path)


# Utility function to check if sunset date has passed
def is_past_sunset(path: str) -> bool:
    """Check if an endpoint is past its sunset date."""
    info = DEPRECATED_ENDPOINTS.get(path)
    if not info or "sunset" not in info:
        return False

    try:
        sunset = datetime.fromisoformat(info["sunset"])
        return datetime.now(timezone.utc) > sunset
    except ValueError:
        return False
