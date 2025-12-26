# API Changelog

All notable changes to the ActorHub.ai API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this API adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## API Version Policy

- **Breaking changes** increment the major version (v1 -> v2)
- **New features** are added to the current version
- **Deprecations** are announced 90 days before removal
- **Sunset headers** are added to deprecated endpoints

---

## [Unreleased]

### Added
- Standardized pagination metadata for all list endpoints
- Response wrapper pattern with `success`, `data`, and `meta` fields
- New error codes for payment, identity, and GDPR operations
- `IdentityListResponse` schema with proper pagination
- `ActorPackListResponse` schema with proper pagination

### Changed
- **BREAKING**: `GET /identity/gallery` now returns paginated response with `data` array
- **BREAKING**: `GET /identity/mine` now returns paginated response with `data` array
- **BREAKING**: Pagination parameter changed from `skip` to `page` (1-indexed)
- Consolidated duplicate schemas across endpoints
- Unified error code definitions in `ErrorCodes` class

### Deprecated
- `skip` parameter on list endpoints (use `page` instead)
- Direct array responses (use wrapped responses with `data` field)

### Migration Guide

#### Pagination Changes

**Before (v1.0):**
```json
GET /api/v1/identity/gallery?skip=0&limit=50

Response: [
  { "id": "...", "display_name": "..." },
  ...
]
```

**After (v1.1):**
```json
GET /api/v1/identity/gallery?page=1&limit=50

Response: {
  "success": true,
  "data": [
    { "id": "...", "display_name": "..." },
    ...
  ],
  "meta": {
    "page": 1,
    "limit": 50,
    "total": 100,
    "total_pages": 2,
    "has_next": true,
    "has_prev": false
  }
}
```

#### Response Wrapper Pattern

All list endpoints now return wrapped responses:
- `success`: Boolean indicating request success
- `data`: Array of items
- `meta`: Pagination metadata

---

## [1.0.0] - 2024-12-01

### Added
- Initial API release
- Identity registration with face verification
- Liveness detection for selfie verification
- Actor Pack training and management
- Marketplace listings and licensing
- Stripe payment integration
- Subscription management
- Admin dashboard endpoints
- Analytics and reporting
- GDPR compliance endpoints
- Notification system

### Endpoints

#### Identity
- `POST /api/v1/identity/register` - Register new identity
- `GET /api/v1/identity/gallery` - Public gallery
- `GET /api/v1/identity/mine` - User's identities
- `GET /api/v1/identity/{id}` - Get identity details
- `PATCH /api/v1/identity/{id}` - Update identity
- `DELETE /api/v1/identity/{id}` - Delete identity
- `POST /api/v1/identity/verify` - Verify image for protected identities

#### Marketplace
- `GET /api/v1/marketplace/listings` - Browse listings
- `GET /api/v1/marketplace/listings/{id}` - Get listing
- `POST /api/v1/marketplace/listings` - Create listing
- `POST /api/v1/marketplace/license/purchase` - Purchase license
- `GET /api/v1/marketplace/licenses/mine` - User's licenses

#### Subscriptions
- `GET /api/v1/subscriptions/current` - Current subscription
- `GET /api/v1/subscriptions/plans` - Available plans
- `POST /api/v1/subscriptions/checkout` - Create checkout
- `POST /api/v1/subscriptions/cancel` - Cancel subscription

#### Admin
- `GET /api/v1/admin/dashboard` - Dashboard stats
- `GET /api/v1/admin/users` - List users
- `GET /api/v1/admin/audit-logs` - Audit logs

---

## Deprecation Schedule

| Endpoint/Feature | Deprecated | Sunset Date | Replacement |
|-----------------|------------|-------------|-------------|
| `skip` pagination param | v1.1 | v2.0 | `page` parameter |
| Direct array responses | v1.1 | v2.0 | Wrapped responses |

---

## Error Codes Reference

### Authentication & Authorization
- `UNAUTHORIZED` - Authentication required
- `FORBIDDEN` - Insufficient permissions
- `INVALID_TOKEN` - Token is invalid or malformed
- `TOKEN_EXPIRED` - Token has expired

### Payment Errors
- `PAYMENT_ERROR` - General payment failure
- `PAYMENT_NOT_CONFIGURED` - Stripe not configured
- `REFUND_FAILED` - Refund processing failed
- `REFUND_WINDOW_EXPIRED` - Refund window has passed

### Identity Errors
- `DUPLICATE_IDENTITY` - Face already registered
- `LIVENESS_CHECK_FAILED` - Liveness verification failed
- `FACE_NOT_DETECTED` - No face found in image

### Rate Limiting
- `RATE_LIMITED` - Too many requests
- `API_CALLS_EXCEEDED` - Monthly API limit reached

---

## Versioning Headers

All responses include:
- `X-API-Version: 1.0` - Current API version
- `X-Request-ID: uuid` - Request tracking ID

Deprecated endpoints include:
- `Deprecation: <date>` - When feature was deprecated
- `Sunset: <date>` - When feature will be removed
- `Link: </new-endpoint>; rel="successor-version"` - New endpoint URL
