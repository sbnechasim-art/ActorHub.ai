"""Licensing Service API Routes."""

import structlog
import jwt
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

from .config import get_settings, Settings

router = APIRouter(tags=["licensing"])
logger = structlog.get_logger()


class LicenseType(str, Enum):
    PERSONAL = "personal"
    COMMERCIAL = "commercial"
    EXTENDED = "extended"


class LicenseTier(str, Enum):
    FREE = "free"
    CREATOR = "creator"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class LicenseRequest(BaseModel):
    """License creation request."""
    actor_pack_id: str = Field(..., description="Actor pack ID")
    user_id: str = Field(..., description="User ID")
    license_type: LicenseType = Field(default=LicenseType.PERSONAL)
    tier: LicenseTier = Field(default=LicenseTier.FREE)


class License(BaseModel):
    """License details."""
    license_id: str
    actor_pack_id: str
    user_id: str
    license_type: LicenseType
    tier: LicenseTier
    token: str
    generations_used: int
    generations_limit: int
    created_at: datetime
    expires_at: datetime
    is_active: bool


class UsageCheck(BaseModel):
    """Usage check result."""
    allowed: bool
    remaining: int
    limit: int
    message: str


class GenerationRecord(BaseModel):
    """Generation usage record."""
    license_id: str
    generation_id: str
    timestamp: datetime
    prompt: Optional[str] = None


def get_settings_dep() -> Settings:
    return get_settings()


# In-memory storage (use database in production)
licenses: dict[str, License] = {}
usage_records: dict[str, list[GenerationRecord]] = {}


def get_generation_limit(tier: LicenseTier, settings: Settings) -> int:
    """Get generation limit for tier."""
    limits = {
        LicenseTier.FREE: settings.free_generation_limit,
        LicenseTier.CREATOR: settings.creator_generation_limit,
        LicenseTier.PROFESSIONAL: settings.pro_generation_limit,
        LicenseTier.ENTERPRISE: 999999,  # Unlimited
    }
    return limits.get(tier, settings.free_generation_limit)


@router.post("/licenses", response_model=License)
async def create_license(
    request: LicenseRequest,
    settings: Settings = Depends(get_settings_dep),
):
    """Create a new license for an actor pack."""
    logger.info(
        "Creating license",
        actor_pack_id=request.actor_pack_id,
        user_id=request.user_id,
        license_type=request.license_type,
    )

    license_id = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + timedelta(days=settings.license_expiry_days)

    # Generate license token
    token_payload = {
        "license_id": license_id,
        "actor_pack_id": request.actor_pack_id,
        "user_id": request.user_id,
        "license_type": request.license_type.value,
        "tier": request.tier.value,
        "iat": now.timestamp(),
        "exp": expires_at.timestamp(),
    }

    token = jwt.encode(
        token_payload,
        settings.license_secret_key,
        algorithm=settings.license_algorithm,
    )

    generation_limit = get_generation_limit(request.tier, settings)

    license = License(
        license_id=license_id,
        actor_pack_id=request.actor_pack_id,
        user_id=request.user_id,
        license_type=request.license_type,
        tier=request.tier,
        token=token,
        generations_used=0,
        generations_limit=generation_limit,
        created_at=now,
        expires_at=expires_at,
        is_active=True,
    )

    licenses[license_id] = license
    usage_records[license_id] = []

    logger.info("License created", license_id=license_id)
    return license


@router.get("/licenses/{license_id}", response_model=License)
async def get_license(license_id: str):
    """Get license details."""
    if license_id not in licenses:
        raise HTTPException(status_code=404, detail="License not found")
    return licenses[license_id]


@router.get("/licenses/user/{user_id}", response_model=list[License])
async def get_user_licenses(user_id: str):
    """Get all licenses for a user."""
    user_licenses = [l for l in licenses.values() if l.user_id == user_id]
    return user_licenses


@router.post("/licenses/{license_id}/verify", response_model=UsageCheck)
async def verify_license(
    license_id: str,
    authorization: str = Header(None, alias="X-License-Token"),
    settings: Settings = Depends(get_settings_dep),
):
    """Verify a license and check usage limits."""
    if license_id not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    license = licenses[license_id]

    # Verify token if provided
    if authorization:
        try:
            payload = jwt.decode(
                authorization,
                settings.license_secret_key,
                algorithms=[settings.license_algorithm],
            )
            if payload.get("license_id") != license_id:
                raise HTTPException(status_code=401, detail="Invalid license token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="License expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid license token")

    # Check if license is active
    if not license.is_active:
        return UsageCheck(
            allowed=False,
            remaining=0,
            limit=license.generations_limit,
            message="License is deactivated",
        )

    # Check expiration
    if datetime.utcnow() > license.expires_at:
        return UsageCheck(
            allowed=False,
            remaining=0,
            limit=license.generations_limit,
            message="License has expired",
        )

    # Check usage limits
    remaining = license.generations_limit - license.generations_used
    if remaining <= 0:
        return UsageCheck(
            allowed=False,
            remaining=0,
            limit=license.generations_limit,
            message="Generation limit reached",
        )

    return UsageCheck(
        allowed=True,
        remaining=remaining,
        limit=license.generations_limit,
        message="License valid",
    )


@router.post("/licenses/{license_id}/use")
async def record_usage(
    license_id: str,
    generation_id: str,
    prompt: Optional[str] = None,
):
    """Record a generation usage against a license."""
    if license_id not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    license = licenses[license_id]

    # Check limits
    if license.generations_used >= license.generations_limit:
        raise HTTPException(status_code=429, detail="Generation limit reached")

    # Record usage
    record = GenerationRecord(
        license_id=license_id,
        generation_id=generation_id,
        timestamp=datetime.utcnow(),
        prompt=prompt,
    )
    usage_records[license_id].append(record)

    # Update license
    license.generations_used += 1

    logger.info(
        "Usage recorded",
        license_id=license_id,
        generation_id=generation_id,
        used=license.generations_used,
        limit=license.generations_limit,
    )

    return {
        "recorded": True,
        "generations_used": license.generations_used,
        "generations_remaining": license.generations_limit - license.generations_used,
    }


@router.get("/licenses/{license_id}/usage", response_model=list[GenerationRecord])
async def get_usage_history(license_id: str, limit: int = 100, offset: int = 0):
    """Get usage history for a license."""
    if license_id not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    records = usage_records.get(license_id, [])
    return records[offset : offset + limit]


@router.post("/licenses/{license_id}/deactivate")
async def deactivate_license(license_id: str):
    """Deactivate a license."""
    if license_id not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    licenses[license_id].is_active = False
    logger.info("License deactivated", license_id=license_id)

    return {"message": "License deactivated", "license_id": license_id}


@router.post("/licenses/{license_id}/upgrade")
async def upgrade_license(
    license_id: str,
    new_tier: LicenseTier,
    settings: Settings = Depends(get_settings_dep),
):
    """Upgrade a license to a higher tier."""
    if license_id not in licenses:
        raise HTTPException(status_code=404, detail="License not found")

    license = licenses[license_id]
    old_tier = license.tier

    # Update tier and limit
    license.tier = new_tier
    license.generations_limit = get_generation_limit(new_tier, settings)

    logger.info(
        "License upgraded",
        license_id=license_id,
        old_tier=old_tier,
        new_tier=new_tier,
    )

    return {
        "message": "License upgraded",
        "license_id": license_id,
        "old_tier": old_tier,
        "new_tier": new_tier,
        "new_limit": license.generations_limit,
    }
