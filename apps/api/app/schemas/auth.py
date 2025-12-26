"""Authentication-related schemas"""

from typing import List

from pydantic import BaseModel, EmailStr


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str


class EmailVerificationRequest(BaseModel):
    """Schema for email verification"""
    token: str


class Enable2FAResponse(BaseModel):
    """Response when enabling 2FA"""
    secret: str
    qr_code: str
    backup_codes: List[str]


class Verify2FARequest(BaseModel):
    """Request to verify 2FA code"""
    code: str


class Verify2FALogin(BaseModel):
    """
    Login with 2FA code.

    SECURITY FIX: Changed from user_id to pending_token.
    The pending_token is a short-lived JWT that proves the user
    has already passed password authentication. This prevents
    account takeover attacks where an attacker could guess user_ids.
    """
    pending_token: str
    code: str


class TwoFactorRequiredResponse(BaseModel):
    """Response when 2FA is required during login"""
    requires_2fa: bool = True
    pending_token: str
    message: str = "Two-factor authentication required"
