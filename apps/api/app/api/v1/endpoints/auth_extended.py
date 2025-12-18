"""
Extended Authentication Endpoints
Password Reset, Email Verification, 2FA
"""

import base64
import io
import secrets
from datetime import datetime, timedelta

import pyotp
import qrcode
import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.user import User

logger = structlog.get_logger()
router = APIRouter()


# ===========================================
# Schemas
# ===========================================


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class EmailVerificationRequest(BaseModel):
    token: str


class Enable2FAResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: list[str]


class Verify2FARequest(BaseModel):
    code: str


class Verify2FALogin(BaseModel):
    user_id: str
    code: str


# ===========================================
# Password Reset
# ===========================================


@router.post("/password-reset/request")
async def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset email.
    Always returns success to prevent email enumeration.
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user:
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        await db.commit()

        # Send email in background
        background_tasks.add_task(
            send_password_reset_email, email=user.email, token=reset_token, name=user.first_name
        )

        logger.info("Password reset requested", email=request.email)

    # Always return success
    return {"message": "If an account exists, a reset email has been sent."}


@router.post("/password-reset/confirm")
async def confirm_password_reset(request: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """Confirm password reset with token"""
    # Fetch user with active reset token
    result = await db.execute(
        select(User).where(
            User.password_reset_token.isnot(None),
            User.password_reset_expires > datetime.utcnow(),
        )
    )
    users_with_tokens = result.scalars().all()

    # Use constant-time comparison to prevent timing attacks
    user = None
    for u in users_with_tokens:
        if u.password_reset_token and secrets.compare_digest(u.password_reset_token, request.token):
            user = u
            break

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    # Validate password strength
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Update password
    user.hashed_password = hash_password(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.commit()

    logger.info("Password reset completed", user_id=str(user.id))

    return {"message": "Password has been reset successfully"}


# ===========================================
# Email Verification
# ===========================================


@router.post("/verify-email/send")
async def send_verification_email(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send email verification link"""
    if current_user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    current_user.email_verification_token = verification_token
    current_user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
    await db.commit()

    # Send email
    background_tasks.add_task(
        send_verification_email_task,
        email=current_user.email,
        token=verification_token,
        name=current_user.first_name,
    )

    return {"message": "Verification email sent"}


@router.post("/verify-email/confirm")
async def confirm_email_verification(
    request: EmailVerificationRequest, db: AsyncSession = Depends(get_db)
):
    """Confirm email with verification token"""
    # Fetch users with active verification tokens
    result = await db.execute(
        select(User).where(
            User.email_verification_token.isnot(None),
            User.email_verification_expires > datetime.utcnow(),
        )
    )
    users_with_tokens = result.scalars().all()

    # Use constant-time comparison to prevent timing attacks
    user = None
    for u in users_with_tokens:
        if u.email_verification_token and secrets.compare_digest(u.email_verification_token, request.token):
            user = u
            break

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user.is_verified = True
    user.verified_at = datetime.utcnow()
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
async def verify_2fa_login(request: Verify2FALogin, db: AsyncSession = Depends(get_db)):
    """Verify 2FA code during login"""
    result = await db.execute(select(User).where(User.id == request.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail="Invalid request")

    # Check TOTP code
    totp = pyotp.TOTP(user.totp_secret)
    if totp.verify(request.code):
        # Generate access token
        from app.core.security import create_access_token

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

    # Check backup codes
    if user.backup_codes and request.code.upper() in user.backup_codes:
        user.backup_codes.remove(request.code.upper())
        await db.commit()

        from app.core.security import create_access_token

        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(status_code=400, detail="Invalid code")


# ===========================================
# Email Helper Functions
# ===========================================


async def send_email(to_email: str, subject: str, html_content: str):
    """
    Send email using SendGrid.
    Falls back to logging in development mode.
    """
    if not settings.SENDGRID_API_KEY:
        logger.warning(f"Email not sent (no API key): {subject} -> {to_email}")
        return

    try:
        import sendgrid
        from sendgrid.helpers.mail import Content, Email, Mail, To

        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        from_email = Email(settings.EMAIL_FROM, settings.EMAIL_FROM_NAME)
        to_email_obj = To(to_email)
        content = Content("text/html", html_content)
        mail = Mail(from_email, to_email_obj, subject, content)

        response = sg.client.mail.send.post(request_body=mail.get())
        logger.info(f"Email sent: {subject} -> {to_email}, status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise


async def send_password_reset_email(email: str, token: str, name: str):
    """Send password reset email"""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Password Reset Request</h2>
        <p>Hi {name or 'there'},</p>
        <p>We received a request to reset your password. Click the button below to create a new password:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Reset Password</a>
        </p>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #666; font-size: 12px;">ActorHub.ai - Protect Your Digital Identity</p>
    </body>
    </html>
    """

    await send_email(email, "Reset Your ActorHub.ai Password", html_content)
    logger.info(f"Password reset email sent to {email}")


async def send_verification_email_task(email: str, token: str, name: str):
    """Send email verification email"""
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html_content = f"""
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

    await send_email(email, "Verify Your ActorHub.ai Email", html_content)
    logger.info(f"Verification email sent to {email}")
