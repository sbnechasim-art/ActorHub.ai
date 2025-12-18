"""User schemas"""

import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Schema for login request"""

    email: EmailStr
    password: str


class UserCreate(BaseModel):
    """Schema for creating a new user"""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        # Check for common weak passwords
        weak_passwords = ['password', '12345678', 'qwerty123', 'admin123', 'letmein1']
        if v.lower() in weak_passwords:
            raise ValueError('Password is too common. Please choose a stronger password')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user info"""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    preferences: Optional[dict] = None
    notification_settings: Optional[dict] = None


class UserResponse(BaseModel):
    """Schema for user response"""

    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    tier: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class ApiKeyCreate(BaseModel):
    """Schema for creating API key"""

    name: str = Field(..., min_length=1, max_length=100)
    permissions: List[str] = Field(default=["verify"])
    rate_limit: int = Field(default=100, ge=1, le=10000)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class ApiKeyResponse(BaseModel):
    """Schema for API key response"""

    id: UUID
    name: str
    key_prefix: str
    permissions: List[str]
    rate_limit: int
    is_active: bool
    usage_count: int
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreatedResponse(BaseModel):
    """Response when API key is first created (includes full key)"""

    api_key: str  # Full key - only shown once
    key_info: ApiKeyResponse
