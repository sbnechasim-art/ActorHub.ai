"""API v1 routes"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    actor_packs,
    admin,
    analytics,
    auth_extended,
    gdpr,
    generation,
    health,
    identity,
    marketplace,
    notifications,
    oauth,
    refunds,
    subscriptions,
    users,
    webhooks,
)

router = APIRouter()

# Include all endpoint routers
router.include_router(identity.router, prefix="/identity", tags=["Identity"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(marketplace.router, prefix="/marketplace", tags=["Marketplace"])
router.include_router(actor_packs.router, prefix="/actor-packs", tags=["Actor Packs"])
router.include_router(generation.router, prefix="/generate", tags=["Content Generation"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

# Auth extended (2FA, password reset, email verification)
router.include_router(auth_extended.router, prefix="/auth", tags=["Authentication"])

# OAuth (Google, GitHub)
router.include_router(oauth.router, prefix="/oauth", tags=["OAuth"])

# Analytics & Reporting
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

# Notifications
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])

# Subscriptions & Billing
router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])

# Refunds
router.include_router(refunds.router, prefix="/refunds", tags=["Refunds"])

# Admin (requires admin role)
router.include_router(admin.router, prefix="/admin", tags=["Admin"])

# GDPR compliance endpoints
router.include_router(gdpr.router, prefix="/gdpr", tags=["GDPR"])

# Health checks (also available at root level)
router.include_router(health.router, prefix="/health", tags=["Health"])
