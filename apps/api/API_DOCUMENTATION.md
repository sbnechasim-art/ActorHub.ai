# ActorHub.ai API Documentation

**Version:** 1.0.0
**Base URL:** `https://api.actorhub.ai/api/v1`
**Interactive Docs:** `https://api.actorhub.ai/docs`

## Overview

ActorHub.ai API provides endpoints for:
- **Identity Management** - Register and protect digital identities
- **Verification** - Check if images contain protected identities
- **Marketplace** - Browse and license identities
- **Actor Packs** - AI-ready models for licensed identities

## Authentication

### JWT Token Authentication

Most endpoints require a Bearer token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

### API Key Authentication

For programmatic access, use an API key:

```bash
X-API-Key: ah_your_api_key_here
```

### Obtaining Tokens

```bash
# Login
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

## Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/health/ready` | GET | Readiness probe (includes DB check) |
| `/health/detailed` | GET | Detailed health with all services |

### Authentication (`/auth`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/register` | POST | - | Create new account |
| `/auth/login` | POST | - | Login and get tokens |
| `/auth/refresh` | POST | - | Refresh access token |
| `/auth/logout` | POST | JWT | Logout and invalidate tokens |
| `/auth/forgot-password` | POST | - | Request password reset |
| `/auth/reset-password` | POST | - | Reset password with token |

### Identity (`/identity`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/identity/register` | POST | JWT | Register a new identity |
| `/identity/verify` | POST | JWT/API Key | Verify image against database |
| `/identity/mine` | GET | JWT | Get user's identities |
| `/identity/{id}` | GET | JWT | Get identity details |
| `/identity/{id}` | PATCH | JWT | Update identity settings |

#### Register Identity

```bash
POST /identity/register
Content-Type: multipart/form-data
Authorization: Bearer <token>

# Form fields:
display_name: "John Actor"
protection_level: "pro"  # free, pro, enterprise
allow_commercial: true
allow_ai_training: false

# Files:
face_image: <file>  # Primary face photo
verification_image: <file>  # Selfie for verification
```

#### Verify Image

```bash
POST /identity/verify
Content-Type: application/json
Authorization: Bearer <token>

{
  "image_base64": "<base64_encoded_image>",
  // OR
  "image_url": "https://allowed-domain.com/image.jpg",
  "include_license_options": true
}

# Response
{
  "matches": [
    {
      "identity_id": "uuid",
      "identity_name": "John Actor",
      "similarity_score": 0.95,
      "confidence": "high",
      "protection_status": "protected",
      "license_required": true,
      "license_options": [
        {"type": "single_use", "price_usd": 29.99},
        {"type": "subscription", "price_usd": 99.99}
      ]
    }
  ],
  "total_faces_detected": 1,
  "processing_time_ms": 245
}
```

### Marketplace (`/marketplace`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/marketplace/listings` | GET | - | Browse listings |
| `/marketplace/listings/{id}` | GET | - | Get listing details |
| `/marketplace/categories` | GET | - | Get categories |
| `/marketplace/license/price` | POST | JWT | Calculate license price |
| `/marketplace/license/purchase` | POST | JWT | Start purchase flow |
| `/marketplace/licenses/mine` | GET | JWT | Get user's licenses |
| `/marketplace/licenses/{id}` | GET | JWT | Get license details |

#### Calculate Price

```bash
POST /marketplace/license/price
Content-Type: application/json
Authorization: Bearer <token>

{
  "identity_id": "uuid",
  "license_type": "single_use",  # single_use, subscription, unlimited
  "usage_type": "commercial",    # personal, commercial, editorial
  "duration_days": 30
}

# Response
{
  "base_price": 50.00,
  "duration_multiplier": 1.0,
  "usage_multiplier": 2.0,
  "platform_fee": 5.00,
  "total_price": 105.00,
  "currency": "USD",
  "breakdown": {
    "base": 50.00,
    "usage_adjustment": 50.00,
    "platform_fee": 5.00
  }
}
```

#### Purchase License

```bash
POST /marketplace/license/purchase
Content-Type: application/json
Authorization: Bearer <token>

{
  "identity_id": "uuid",
  "license_type": "single_use",
  "usage_type": "commercial",
  "duration_days": 30,
  "project_name": "Marketing Campaign 2024"
}

# Response
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_...",
  "price_usd": 105.00,
  "license_details": {
    "type": "single_use",
    "usage": "commercial",
    "duration_days": 30
  }
}
```

### Actor Packs (`/actor-pack`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/actor-pack/public` | GET | - | Browse available packs |
| `/actor-pack/train` | POST | JWT | Start training |
| `/actor-pack/status/{id}` | GET | JWT | Get training status |
| `/actor-pack/download/{identity_id}` | GET | JWT | Download pack (requires license) |

### User Management (`/users`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/users/me` | GET | JWT | Get current user |
| `/users/me` | PATCH | JWT | Update profile |
| `/users/me/dashboard` | GET | JWT | Get dashboard data |
| `/users/api-keys` | GET | JWT | List API keys |
| `/users/api-keys` | POST | JWT | Create API key |
| `/users/api-keys/{id}` | DELETE | JWT | Revoke API key |

### Refunds (`/refunds`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/refunds/policy` | GET | - | Get refund policy |
| `/refunds/request` | POST | JWT | Request a refund |
| `/refunds/status/{id}` | GET | JWT | Check refund status |
| `/refunds/history` | GET | JWT | Get refund history |

### Analytics (`/analytics`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/analytics/dashboard` | GET | JWT | Get analytics dashboard |
| `/analytics/usage` | GET | JWT | Get usage stats |
| `/analytics/revenue` | GET | JWT | Get revenue stats |

### Notifications (`/notifications`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/notifications` | GET | JWT | Get notifications |
| `/notifications/unread-count` | GET | JWT | Get unread count |
| `/notifications/{id}/read` | POST | JWT | Mark as read |
| `/notifications/read-all` | POST | JWT | Mark all as read |

### Subscriptions (`/subscriptions`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/subscriptions/plans` | GET | - | Get available plans |
| `/subscriptions/current` | GET | JWT | Get current subscription |
| `/subscriptions/checkout` | POST | JWT | Start subscription |
| `/subscriptions/cancel` | POST | JWT | Cancel subscription |

### Webhooks (`/webhooks`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhooks/stripe` | POST | Stripe payment events |
| `/webhooks/clerk` | POST | Clerk auth events |
| `/webhooks/replicate` | POST | Training completion events |

### Admin (`/admin`) - Admin Only

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/admin/dashboard` | GET | Admin | Admin dashboard stats |
| `/admin/users` | GET | Admin | List all users |
| `/admin/users/{id}` | GET | Admin | Get user details |
| `/admin/users/{id}` | PATCH | Admin | Update user |
| `/admin/audit-logs` | GET | Admin | Get audit logs |
| `/admin/webhooks` | GET | Admin | Get webhook events |
| `/admin/payouts/pending` | GET | Admin | Get pending payouts |
| `/admin/payouts/{id}/approve` | POST | Admin | Approve payout |

---

## Rate Limits

| Tier | General | Login | Register |
|------|---------|-------|----------|
| Anonymous | 30/min | 5/min | 3/min |
| Free | 60/min | 5/min | 3/min |
| Pro | 300/min | 5/min | 3/min |
| Enterprise | 1000/min | 5/min | 3/min |

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 58
X-RateLimit-Reset: 1703088000
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human readable message",
  "details": {}
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `unauthorized` | 401 | Missing or invalid token |
| `forbidden` | 403 | Insufficient permissions |
| `not_found` | 404 | Resource not found |
| `validation_error` | 422 | Invalid request data |
| `rate_limit_exceeded` | 429 | Too many requests |
| `internal_error` | 500 | Server error |

---

## SDKs & Libraries

- **JavaScript/TypeScript SDK:** `@actorhub/sdk`
- **Python SDK:** Coming soon
- **REST API:** Use any HTTP client

### JavaScript Example

```javascript
import { ActorHubClient } from '@actorhub/sdk';

const client = new ActorHubClient({
  apiKey: 'ah_your_api_key'
});

// Verify an image
const result = await client.identity.verify({
  imageUrl: 'https://example.com/photo.jpg'
});

console.log(result.matches);
```

---

## Webhooks

### Configuring Webhooks

Configure webhook endpoints in your dashboard or contact support.

### Webhook Events

| Event | Description |
|-------|-------------|
| `license.purchased` | License purchase completed |
| `license.expired` | License has expired |
| `training.completed` | Actor Pack training finished |
| `training.failed` | Actor Pack training failed |
| `identity.verified` | Identity verification completed |

### Webhook Payload

```json
{
  "event": "license.purchased",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "license_id": "uuid",
    "identity_id": "uuid",
    "price_usd": 105.00
  }
}
```

### Verifying Signatures

All webhooks include a signature header for verification:

```
X-ActorHub-Signature: sha256=abc123...
```

---

## Support

- **Documentation:** https://docs.actorhub.ai
- **Status:** https://status.actorhub.ai
- **Email:** support@actorhub.ai
- **Discord:** https://discord.gg/actorhub
