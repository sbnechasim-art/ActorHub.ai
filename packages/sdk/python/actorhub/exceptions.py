"""
Exceptions for ActorHub SDK
"""


class ActorHubError(Exception):
    """Base exception for ActorHub SDK"""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(ActorHubError):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class NotFoundError(ActorHubError):
    """Raised when a resource is not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(ActorHubError):
    """Raised when request validation fails"""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=400)


class RateLimitError(ActorHubError):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class LicenseRequiredError(ActorHubError):
    """Raised when a license is required"""
    def __init__(self, identity_id: str, identity_name: str):
        message = f"License required for identity: {identity_name}"
        super().__init__(message, status_code=403)
        self.identity_id = identity_id
        self.identity_name = identity_name
