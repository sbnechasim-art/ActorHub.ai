"""
OAuth Authentication Endpoints
Google and GitHub OAuth login/signup
"""

import secrets
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.helpers import utc_now  # MEDIUM FIX: Use timezone-aware datetime
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User

logger = structlog.get_logger()
router = APIRouter()

# OAuth state serializer for CSRF protection
state_serializer = URLSafeTimedSerializer(settings.OAUTH_STATE_SECRET)

# OAuth provider configurations
OAUTH_PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": ["openid", "email", "profile"],
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "emails_url": "https://api.github.com/user/emails",
        "scopes": ["user:email", "read:user"],
    },
}


def get_oauth_redirect_uri(provider: str) -> str:
    """Get the OAuth callback URL for a provider"""
    return f"{settings.FRONTEND_URL}/api/auth/{provider}/callback"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly cookies for authentication tokens."""
    response.set_cookie(
        key=settings.COOKIE_ACCESS_TOKEN_NAME,
        value=access_token,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )
    response.set_cookie(
        key=settings.COOKIE_REFRESH_TOKEN_NAME,
        value=refresh_token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


# ============================================
# Google OAuth
# ============================================

@router.get("/google/authorize")
async def google_authorize(redirect_uri: Optional[str] = None):
    """
    Initiate Google OAuth flow.
    Returns the authorization URL to redirect the user to.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(500, "Google OAuth not configured")

    # Generate state for CSRF protection
    state_data = {"provider": "google", "nonce": secrets.token_urlsafe(16)}
    if redirect_uri:
        state_data["redirect_uri"] = redirect_uri
    state = state_serializer.dumps(state_data)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": get_oauth_redirect_uri("google"),
        "response_type": "code",
        "scope": " ".join(OAUTH_PROVIDERS["google"]["scopes"]),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }

    auth_url = f"{OAUTH_PROVIDERS['google']['authorize_url']}?{urlencode(params)}"
    return {"authorization_url": auth_url}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth callback.
    Exchanges code for tokens and creates/updates user.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth not configured")

    # Verify state (CSRF protection)
    try:
        state_data = state_serializer.loads(state, max_age=600)  # 10 minutes
        if state_data.get("provider") != "google":
            raise HTTPException(400, "Invalid state")
    except Exception:
        raise HTTPException(400, "Invalid or expired state")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            OAUTH_PROVIDERS["google"]["token_url"],
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": get_oauth_redirect_uri("google"),
            },
        )

        if token_response.status_code != 200:
            logger.error("Google token exchange failed", response=token_response.text)
            raise HTTPException(400, "Failed to authenticate with Google")

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        # Get user info
        userinfo_response = await client.get(
            OAUTH_PROVIDERS["google"]["userinfo_url"],
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(400, "Failed to get user info from Google")

        userinfo = userinfo_response.json()

    # Extract user data
    google_id = userinfo.get("id")
    email = userinfo.get("email")
    first_name = userinfo.get("given_name")
    last_name = userinfo.get("family_name")
    avatar_url = userinfo.get("picture")
    email_verified = userinfo.get("verified_email", False)

    if not email:
        raise HTTPException(400, "Email not provided by Google")

    # Find or create user (exclude soft-deleted users)
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    # Clean up soft-deleted user with same email if exists
    if not user:
        deleted_result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.isnot(None))
        )
        deleted_user = deleted_result.scalar_one_or_none()
        if deleted_user:
            await db.delete(deleted_user)
            await db.flush()

    if user:
        # Update existing user's OAuth info
        user.oauth_provider = user.oauth_provider or "google"
        user.oauth_provider_id = user.oauth_provider_id or google_id
        oauth_accounts = user.oauth_accounts or {}
        oauth_accounts["google"] = {
            "id": google_id,
            "email": email,
            "connected_at": utc_now().isoformat(),
        }
        user.oauth_accounts = oauth_accounts
        user.avatar_url = user.avatar_url or avatar_url
        user.email_verified = user.email_verified or email_verified
        user.last_login_at = utc_now()
    else:
        # Create new user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            display_name=f"{first_name} {last_name}".strip() if first_name else email.split("@")[0],
            avatar_url=avatar_url,
            email_verified=email_verified,
            oauth_provider="google",
            oauth_provider_id=google_id,
            oauth_accounts={"google": {
                "id": google_id,
                "email": email,
                "connected_at": utc_now().isoformat(),
            }},
            last_login_at=utc_now(),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    # Create JWT tokens
    token_data = {"sub": str(user.id), "email": user.email}
    jwt_access_token = create_access_token(token_data)
    jwt_refresh_token = create_refresh_token(token_data)

    # Redirect to frontend with tokens
    redirect_uri = state_data.get("redirect_uri", "/dashboard")
    redirect_url = f"{settings.FRONTEND_URL}{redirect_uri}?auth_success=true"

    response = RedirectResponse(url=redirect_url, status_code=302)
    _set_auth_cookies(response, jwt_access_token, jwt_refresh_token)

    logger.info("Google OAuth login successful", user_id=str(user.id), email=email)
    return response


# ============================================
# GitHub OAuth
# ============================================

@router.get("/github/authorize")
async def github_authorize(redirect_uri: Optional[str] = None):
    """
    Initiate GitHub OAuth flow.
    Returns the authorization URL to redirect the user to.
    """
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(500, "GitHub OAuth not configured")

    # Generate state for CSRF protection
    state_data = {"provider": "github", "nonce": secrets.token_urlsafe(16)}
    if redirect_uri:
        state_data["redirect_uri"] = redirect_uri
    state = state_serializer.dumps(state_data)

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": get_oauth_redirect_uri("github"),
        "scope": " ".join(OAUTH_PROVIDERS["github"]["scopes"]),
        "state": state,
    }

    auth_url = f"{OAUTH_PROVIDERS['github']['authorize_url']}?{urlencode(params)}"
    return {"authorization_url": auth_url}


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle GitHub OAuth callback.
    Exchanges code for tokens and creates/updates user.
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(500, "GitHub OAuth not configured")

    # Verify state (CSRF protection)
    try:
        state_data = state_serializer.loads(state, max_age=600)  # 10 minutes
        if state_data.get("provider") != "github":
            raise HTTPException(400, "Invalid state")
    except Exception:
        raise HTTPException(400, "Invalid or expired state")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            OAUTH_PROVIDERS["github"]["token_url"],
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": get_oauth_redirect_uri("github"),
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            logger.error("GitHub token exchange failed", response=token_response.text)
            raise HTTPException(400, "Failed to authenticate with GitHub")

        tokens = token_response.json()
        access_token = tokens.get("access_token")

        if not access_token:
            error = tokens.get("error_description", "Unknown error")
            raise HTTPException(400, f"GitHub authentication failed: {error}")

        # Get user info
        userinfo_response = await client.get(
            OAUTH_PROVIDERS["github"]["userinfo_url"],
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(400, "Failed to get user info from GitHub")

        userinfo = userinfo_response.json()

        # Get user emails (may need separate request for private emails)
        emails_response = await client.get(
            OAUTH_PROVIDERS["github"]["emails_url"],
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

        primary_email = None
        email_verified = False
        if emails_response.status_code == 200:
            emails = emails_response.json()
            for email_data in emails:
                if email_data.get("primary"):
                    primary_email = email_data.get("email")
                    email_verified = email_data.get("verified", False)
                    break

    # Extract user data
    github_id = str(userinfo.get("id"))
    email = primary_email or userinfo.get("email")
    name = userinfo.get("name") or userinfo.get("login")
    avatar_url = userinfo.get("avatar_url")
    github_username = userinfo.get("login")

    # Split name into first/last
    name_parts = (name or "").split(" ", 1)
    first_name = name_parts[0] if name_parts else None
    last_name = name_parts[1] if len(name_parts) > 1 else None

    if not email:
        raise HTTPException(400, "Email not available from GitHub. Please make your email public or use email/password login.")

    # Find or create user (exclude soft-deleted users)
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    # Clean up soft-deleted user with same email if exists
    if not user:
        deleted_result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.isnot(None))
        )
        deleted_user = deleted_result.scalar_one_or_none()
        if deleted_user:
            await db.delete(deleted_user)
            await db.flush()

    if user:
        # Update existing user's OAuth info
        user.oauth_provider = user.oauth_provider or "github"
        user.oauth_provider_id = user.oauth_provider_id or github_id
        oauth_accounts = user.oauth_accounts or {}
        oauth_accounts["github"] = {
            "id": github_id,
            "username": github_username,
            "email": email,
            "connected_at": utc_now().isoformat(),
        }
        user.oauth_accounts = oauth_accounts
        user.avatar_url = user.avatar_url or avatar_url
        user.email_verified = user.email_verified or email_verified
        user.last_login_at = utc_now()
    else:
        # Create new user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            display_name=name or github_username or email.split("@")[0],
            avatar_url=avatar_url,
            email_verified=email_verified,
            oauth_provider="github",
            oauth_provider_id=github_id,
            oauth_accounts={"github": {
                "id": github_id,
                "username": github_username,
                "email": email,
                "connected_at": utc_now().isoformat(),
            }},
            last_login_at=utc_now(),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    # Create JWT tokens
    token_data = {"sub": str(user.id), "email": user.email}
    jwt_access_token = create_access_token(token_data)
    jwt_refresh_token = create_refresh_token(token_data)

    # Redirect to frontend with tokens
    redirect_uri = state_data.get("redirect_uri", "/dashboard")
    redirect_url = f"{settings.FRONTEND_URL}{redirect_uri}?auth_success=true"

    response = RedirectResponse(url=redirect_url, status_code=302)
    _set_auth_cookies(response, jwt_access_token, jwt_refresh_token)

    logger.info("GitHub OAuth login successful", user_id=str(user.id), email=email)
    return response


# ============================================
# OAuth Status & Disconnect
# ============================================

@router.get("/providers")
async def get_oauth_providers():
    """
    Get available OAuth providers and their configuration status.
    """
    return {
        "providers": [
            {
                "id": "google",
                "name": "Google",
                "enabled": bool(settings.GOOGLE_CLIENT_ID),
                "icon": "google",
            },
            {
                "id": "github",
                "name": "GitHub",
                "enabled": bool(settings.GITHUB_CLIENT_ID),
                "icon": "github",
            },
        ]
    }
