"""
Extended Authentication Endpoints
Password Reset, Email Verification, 2FA

FIXED: Emails now sent via Celery queue (Redis-backed) instead of memory-based
BackgroundTasks for improved reliability.
"""

import base64
import io
import secrets
from datetime import datetime, timedelta

import httpx
import pyotp
import qrcode
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.core.database import get_db
from app.core.security import get_current_user, hash_password, decode_2fa_pending_token, create_access_token, create_refresh_token
from app.models.user import User
from app.schemas.auth import (
    EmailVerificationRequest,
    Enable2FAResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    Verify2FALogin,
    Verify2FARequest,
)

logger = structlog.get_logger()
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ===========================================
# Password Reset
# ===========================================


@router.post("/password-reset/request")
@limiter.limit("3/minute")
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset email.
    Always returns success to prevent email enumeration.

    Rate limited to 3 requests per minute to prevent abuse.
    """
    result = await db.execute(
        select(User).where(User.email == reset_request.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = reset_token
        user.password_reset_expires = utc_now() + timedelta(hours=1)
        await db.commit()

        # FIXED: Queue email via Celery (Redis-backed) instead of in-memory BackgroundTasks
        await queue_password_reset_email(user.email, reset_token, user.first_name)

        logger.info("Password reset requested")

    # Always return success
    return {"message": "If an account exists, a reset email has been sent."}


@router.post("/password-reset/confirm")
@limiter.limit("5/minute")
async def confirm_password_reset(request: Request, body: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """Confirm password reset with token"""
    # Fetch user with active reset token
    result = await db.execute(
        select(User).where(
            User.password_reset_token.isnot(None),
            User.password_reset_expires > utc_now(),
        )
    )
    users_with_tokens = result.scalars().all()

    # Use constant-time comparison to prevent timing attacks
    user = None
    for u in users_with_tokens:
        if u.password_reset_token and secrets.compare_digest(u.password_reset_token, body.token):
            user = u
            break

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Validate password strength
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Update password
    user.hashed_password = hash_password(body.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    # SECURITY: Set password_changed_at to invalidate all existing sessions
    user.password_changed_at = utc_now()
    await db.commit()

    logger.info("Password reset completed - all sessions invalidated", user_id=str(user.id))

    return {"message": "Password has been reset successfully. Please log in again."}


# ===========================================
# Email Verification
# ===========================================


@router.post("/verify-email/send")
async def send_verification_email(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send email verification link"""
    if current_user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    current_user.email_verification_token = verification_token
    current_user.email_verification_expires = utc_now() + timedelta(hours=24)
    await db.commit()

    # FIXED: Queue email via Celery (Redis-backed) instead of in-memory BackgroundTasks
    await queue_verification_email(current_user.email, verification_token, current_user.first_name)

    return {"message": "Verification email sent"}


@router.post("/verify-email/confirm")
@limiter.limit("10/minute")
async def confirm_email_verification(
    request: Request,
    body: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Confirm email with verification token"""
    # Fetch users with active verification tokens
    result = await db.execute(
        select(User).where(
            User.email_verification_token.isnot(None),
            User.email_verification_expires > utc_now(),
        )
    )
    users_with_tokens = result.scalars().all()

    # Use constant-time comparison to prevent timing attacks
    user = None
    for u in users_with_tokens:
        if u.email_verification_token and secrets.compare_digest(u.email_verification_token, body.token):
            user = u
            break

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user.is_verified = True
    user.verified_at = utc_now()
    user.email_verification_token = None
    user.email_verification_expires = None
    await db.commit()

    return {"message": "Email verified successfully"}


# ===========================================
# Two-Factor Authentication
# ===========================================


@router.post("/2fa/enable", response_model=Enable2FAResponse)
async def enable_2fa(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Enable 2FA for current user"""
    if current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA already enabled")

    # Generate TOTP secret
    secret = pyotp.random_base32()
    current_user.totp_secret = secret

    # Generate backup codes
    backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
    current_user.backup_codes = backup_codes

    await db.commit()

    # Generate QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=current_user.email, issuer_name="ActorHub.ai")

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return Enable2FAResponse(
        secret=secret, qr_code=f"data:image/png;base64,{qr_base64}", backup_codes=backup_codes
    )


@router.post("/2fa/verify")
async def verify_2fa_setup(
    request: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify 2FA setup with TOTP code"""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="2FA not set up")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(request.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    current_user.is_2fa_enabled = True
    await db.commit()

    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(
    request: Verify2FARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA"""
    if not current_user.is_2fa_enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled")

    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(request.code):
        raise HTTPException(status_code=400, detail="Invalid code")

    current_user.totp_secret = None
    current_user.backup_codes = None
    current_user.is_2fa_enabled = False
    await db.commit()

    return {"message": "2FA disabled successfully"}


@router.post("/2fa/verify-login")
@limiter.limit("5/minute")
async def verify_2fa_login(request: Request, body: Verify2FALogin, db: AsyncSession = Depends(get_db)):
    """
    Verify 2FA code during login.

    **SECURITY FIX:** Now requires a pending_token instead of user_id.
    This token is issued after successful password verification and proves
    the user has passed the first authentication factor.

    The pending_token is valid for only 5 minutes to prevent replay attacks.

    **Rate Limiting:** This endpoint is rate limited to prevent brute force
    attacks on TOTP codes.
    """
    # SECURITY: Validate the pending token
    payload = decode_2fa_pending_token(body.pending_token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token. Please login again."
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail="Invalid request")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")

    # Check TOTP code (with window=1 for slight clock skew tolerance)
    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(body.code, valid_window=1):
        # Update last login
        user.last_login_at = utc_now()
        await db.commit()

        # Generate full tokens
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    # Check backup codes
    if user.backup_codes and body.code.upper() in user.backup_codes:
        user.backup_codes.remove(body.code.upper())
        user.last_login_at = utc_now()
        await db.commit()

        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(data=token_data)
        refresh_token = create_refresh_token(data=token_data)

        logger.info("Backup code used for 2FA", user_id=str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    raise HTTPException(status_code=400, detail="Invalid code")


# ===========================================
# Email Queue Functions (via Celery Worker)
# ===========================================

# Worker URL for queuing Celery tasks
WORKER_URL = settings.WORKER_URL if hasattr(settings, 'WORKER_URL') else "http://localhost:8001"


async def queue_password_reset_email(email: str, token: str, name: str):
    """
    Queue password reset email via Celery worker.

    FIXED: Uses Celery queue (Redis-backed) instead of in-memory BackgroundTasks.
    This ensures emails are still sent even if the API server restarts.
    """
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Reset Your ActorHub.ai Password"
    body = f"Hi {name or 'there'}, click here to reset your password: {reset_url}"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Reset Your Password</h2>
        <p>Hi {name or 'there'},</p>
        <p>You requested to reset your password. Click the button below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Reset Password</a>
        </p>
        <p>This link expires in 1 hour. If you didn't request this, ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #666; font-size: 12px;">ActorHub.ai - Protect Your Digital Identity</p>
    </body>
    </html>
    """

    # Queue via Redis/Celery for reliability
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{WORKER_URL}/tasks/send_email",
                json={"to": email, "subject": subject, "body": body, "html": html},
                timeout=5.0
            )
        logger.info("Password reset email queued", email=email)
    except Exception as e:
        # Fallback: log but don't fail the request
        logger.warning(f"Failed to queue password reset email: {e}", email=email)


async def queue_verification_email(email: str, token: str, name: str):
    """
    Queue email verification via Celery worker.

    FIXED: Uses Celery queue (Redis-backed) instead of in-memory BackgroundTasks.
    """
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify Your ActorHub.ai Email"
    body = f"Hi {name or 'there'}, verify your email here: {verify_url}"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Verify Your Email</h2>
        <p>Hi {name or 'there'},</p>
        <p>Thanks for signing up! Please verify your email address by clicking the button below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}" style="background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Verify Email</a>
        </p>
        <p>This link will expire in 24 hours.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #666; font-size: 12px;">ActorHub.ai - Protect Your Digital Identity</p>
    </body>
    </html>
    """

    # Queue via Redis/Celery for reliability
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{WORKER_URL}/tasks/send_email",
                json={"to": email, "subject": subject, "body": body, "html": html},
                timeout=5.0
            )
        logger.info("Verification email queued", email=email)
    except Exception as e:
        # Fallback: log but don't fail the request
        logger.warning(f"Failed to queue verification email: {e}", email=email)
