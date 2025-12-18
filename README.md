# ActorHub.ai

> Digital Identity Protection & Monetization Platform

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Status](https://img.shields.io/badge/status-MVP-yellow)

ActorHub.ai is a platform for protecting and monetizing digital identities. It enables individuals to register their face and likeness, detect unauthorized use, and license their identity for commercial AI projects.

---

## Current Status (Honest Assessment)

| Component | Status | Notes |
|-----------|--------|-------|
| Core API (FastAPI) | **Working** | Routes wired, middleware applied |
| User Auth (Register/Login) | **Working** | `/api/v1/users/register`, `/api/v1/users/login` |
| Identity Management | **Working** | Registration, verification endpoints |
| 2FA / Password Reset | **Working** | `/api/v1/auth/*` endpoints |
| GDPR Compliance | **Working** | `/api/v1/gdpr/*` endpoints |
| Health Checks | **Working** | `/health`, `/api/v1/health/*` |
| Security Headers | **Working** | CSP, HSTS, X-Frame-Options |
| Rate Limiting | **Working** | slowapi + custom middleware |
| Admin Dashboard | **MOCK DATA** | UI only, no real backend API |
| Face Recognition | **Partial** | InsightFace integrated, needs tuning |
| Voice Cloning | **Not Tested** | ElevenLabs API configured |
| Actor Pack Training | **Not Tested** | Replicate API configured |
| Celery Workers | **Not Tested** | Files exist, not verified |
| SDK | **Not Published** | Code complete, not on npm |

### What Works (Happy Path)

1. **Register User** - `POST /api/v1/users/register`
2. **Login** - `POST /api/v1/users/login` (returns JWT)
3. **Get Profile** - `GET /api/v1/users/me` (with token)
4. **Health Check** - `GET /health`

### What Is Mock/Demo

- Admin dashboard statistics (hardcoded values)
- Face similarity scores in some views
- Marketplace listings (demo data)

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [SDK Usage](#sdk-usage)
- [Security](#security)
- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Compliance](#compliance)

---

## Features

### Core Features
- **Identity Registry** - Register and protect your digital identity with AI-powered face recognition (512-dim ArcFace embeddings)
- **Real-time Verification** - API for platforms to check if faces are protected before AI generation (<50ms latency)
- **Marketplace** - License identities for commercial use with automated Stripe payments
- **Actor Packs** - AI-ready model packages for licensed content generation (Face, Voice, Motion)

### Security Features
- **Rate Limiting** - Redis-backed sliding window with per-user/IP/API key tiers
- **2FA Authentication** - TOTP with backup codes
- **Security Headers** - CSP, HSTS, X-Frame-Options, etc.
- **Input Validation** - Request size limits, content-type validation

### Admin & Operations
- **Admin Dashboard** - User management, content moderation, analytics
- **Background Workers** - Celery with training, face recognition, notification queues
- **Scheduled Tasks** - Cleanup, stats aggregation, license expiration checks

### Compliance
- **GDPR Ready** - Data export, right to erasure, consent management
- **Age Verification** - 18+ requirement enforced
- **Terms & Privacy** - Acceptance tracking with timestamps

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LOAD BALANCER                                   │
│                            (Nginx / CloudFront)                              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Frontend  │     │   API Service   │     │ Admin Dashboard │
│   (Next.js 14)  │     │   (FastAPI)     │     │   (Next.js)     │
│   Port: 3000    │     │   Port: 8000    │     │   /admin        │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   PostgreSQL    │     │     Redis       │     │     Qdrant      │
│   (pgvector)    │     │   (Cache/Queue) │     │   (Vector DB)   │
│   Port: 5432    │     │   Port: 6379    │     │   Port: 6333    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────┴────────┐
                        │  Celery Workers │
                        │  ┌───────────┐  │
                        │  │ Training  │  │
                        │  │ Face Rec  │  │
                        │  │ Notific.  │  │
                        │  │ Cleanup   │  │
                        │  └───────────┘  │
                        └─────────────────┘
                                 │
                        ┌────────┴────────┐
                        │     MinIO       │
                        │  (S3 Storage)   │
                        │  Port: 9000     │
                        └─────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+
- pnpm (recommended) or npm

### Development Setup

```bash
# 1. Start infrastructure services
docker compose up -d

# 2. Setup API
cd apps/api
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --port 8000

# 3. Setup Web (new terminal)
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

### Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:3000 | Main web app |
| API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | OpenAPI docs |
| Admin | http://localhost:3000/admin | Admin dashboard |
| PostgreSQL | localhost:5433 | Database |
| Redis | localhost:6380 | Cache/Queue |
| MinIO Console | http://localhost:9001 | S3 storage |
| Qdrant | http://localhost:6333/dashboard | Vector DB |

### Test Credentials

| Account | Email | Password |
|---------|-------|----------|
| Test User | test@actorhub.ai | password123 |
| Admin | admin@actorhub.ai | admin123 |

API Key: `ah_test_key_for_development_only`

---

## Project Structure

```
ActorHub.ai/
├── apps/
│   ├── api/                      # FastAPI Backend
│   │   ├── app/
│   │   │   ├── api/v1/endpoints/ # API endpoints
│   │   │   │   ├── auth.py
│   │   │   │   ├── auth_extended.py   # 2FA, Password Reset
│   │   │   │   ├── identity.py
│   │   │   │   ├── marketplace.py
│   │   │   │   ├── health.py          # Health probes
│   │   │   │   └── gdpr.py            # GDPR compliance
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   ├── database.py
│   │   │   │   ├── security.py
│   │   │   │   └── monitoring.py      # Sentry + Prometheus
│   │   │   ├── middleware/
│   │   │   │   ├── rate_limit.py      # Rate limiting
│   │   │   │   ├── security.py        # Security headers
│   │   │   │   ├── logging.py         # Request logging
│   │   │   │   └── cors.py
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   └── services/
│   │   │       ├── face_recognition.py # InsightFace + Qdrant
│   │   │       ├── training.py         # Actor Pack training
│   │   │       └── storage.py          # S3/MinIO
│   │   ├── tests/                 # Test suite
│   │   │   ├── conftest.py
│   │   │   ├── test_auth.py
│   │   │   ├── test_identity.py
│   │   │   └── test_health.py
│   │   ├── alembic/               # DB migrations
│   │   ├── Dockerfile             # Production container
│   │   └── requirements.txt
│   │
│   ├── web/                       # Next.js Frontend
│   │   ├── src/app/
│   │   │   ├── (dashboard)/       # Dashboard pages
│   │   │   ├── (admin)/admin/     # Admin dashboard
│   │   │   ├── identity/          # Identity registration
│   │   │   ├── marketplace/       # Actor marketplace
│   │   │   ├── privacy/           # Privacy policy
│   │   │   └── terms/             # Terms of service
│   │   ├── Dockerfile
│   │   └── package.json
│   │
│   ├── worker/                    # Celery Workers
│   │   ├── tasks/
│   │   │   ├── training.py        # Actor Pack training
│   │   │   ├── face_recognition.py
│   │   │   ├── notifications.py   # Email/Push/Webhook
│   │   │   └── cleanup.py         # Maintenance
│   │   ├── celery_app.py
│   │   └── Dockerfile
│   │
│   └── studio/                    # Desktop App (Electron)
│       ├── src/main/
│       ├── src/renderer/
│       └── package.json
│
├── packages/
│   └── sdk/                       # Official TypeScript SDK
│       ├── src/
│       │   ├── index.ts
│       │   ├── client.ts
│       │   └── types.ts
│       └── README.md
│
├── nginx/
│   └── nginx.conf                 # Production reverse proxy
│
├── .github/workflows/
│   ├── ci.yml                     # Test + Build + Security scan
│   └── deploy.yml                 # Staging → Production
│
├── docker-compose.yml             # Development
├── docker-compose.prod.yml        # Production
└── PRODUCTION_CHECKLIST.md        # Go/No-Go checklist
```

---

## API Documentation

### Authentication

```bash
# Register
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}

# Login
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
username=user@example.com&password=SecurePass123!

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}

# Enable 2FA
POST /api/v1/auth/2fa/enable
Authorization: Bearer {token}
# Returns: secret, QR code, backup codes
```

### Identity Verification (Core Endpoint)

```bash
# Verify with API key
POST /api/v1/identity/verify
X-API-Key: your-api-key
Content-Type: application/json

{
  "image": "base64-encoded-image",
  "threshold": 0.85
}

# Response
{
  "matched": true,
  "identity_id": "uuid",
  "confidence": 0.92,
  "similarity_score": 0.94,
  "is_authorized": true,
  "license_info": {
    "license_id": "...",
    "valid_until": "2024-12-31"
  }
}
```

### Health Checks

```bash
GET /health      # Basic health
GET /ready       # All dependencies (K8s readiness)
GET /live        # Process alive (K8s liveness)
```

Full API documentation: http://localhost:8000/docs

---

## SDK Usage

### Installation

```bash
npm install @actorhub/sdk
```

### Quick Start

```typescript
import { ActorHub } from '@actorhub/sdk'

const client = new ActorHub({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.actorhub.ai/v1'  // optional
})

// Verify an image
const result = await client.verify({
  image: imageBuffer,  // Buffer or base64 string
  threshold: 0.85
})

if (result.matched) {
  console.log(`Identity: ${result.identity_id}`)
  console.log(`Authorized: ${result.is_authorized}`)
  console.log(`Confidence: ${result.confidence}`)
}

// Register identity
const identity = await client.registerIdentity({
  face_image: faceBuffer,
  verification_image: selfieBuffer,
  display_name: 'John Doe',
  protection_level: 'pro'
})

// Get Actor Pack
const pack = await client.getActorPack(identityId)

// Purchase license
const license = await client.purchaseLicense({
  listing_id: 'listing-123',
  tier_name: 'pro',
  usage_type: 'commercial'
})
```

---

## Security

### Rate Limits

| Tier | Limit | Window |
|------|-------|--------|
| Anonymous | 30 req | 1 min |
| Free | 60 req | 1 min |
| Pro | 300 req | 1 min |
| Enterprise | 1000 req | 1 min |

| Endpoint | Limit | Window |
|----------|-------|--------|
| /auth/login | 10 req | 1 min |
| /auth/register | 5 req | 1 min |
| /identity/register | 5 req | 1 min |
| /identity/verify | 100 req | 1 min |

### Security Headers

All responses include:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy: ...`
- `Referrer-Policy: strict-origin-when-cross-origin`

---

## Deployment

### Production Deployment

```bash
# Build all images
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose exec api alembic upgrade head

# Verify health
curl https://api.actorhub.ai/health
curl https://api.actorhub.ai/ready
```

### CI/CD Pipeline (GitHub Actions)

**CI (on push/PR):**
1. Run tests (pytest, vitest)
2. Lint code (ruff, eslint)
3. Security scan (Trivy, CodeQL)
4. Build Docker images

**CD (on release):**
1. Deploy to staging
2. Run smoke tests
3. Blue-green deploy to production
4. Invalidate CDN cache
5. Create Sentry release

---

## Monitoring

### Prometheus Metrics

Available at `/metrics`:
- `http_requests_total{method, endpoint, status}`
- `http_request_duration_seconds{method, endpoint}`
- `identity_registrations_total{status, protection_level}`
- `identity_verifications_total{matched, authorized}`
- `actor_pack_trainings_total{status}`
- `license_purchases_total{tier, usage_type}`

### Sentry

- Automatic exception capture
- Performance monitoring (traces)
- Release tracking
- PII filtering

### Health Probes

| Endpoint | Purpose | K8s |
|----------|---------|-----|
| `/health` | Basic health | - |
| `/ready` | All dependencies | Readiness probe |
| `/live` | Process alive | Liveness probe |

---

## Compliance

### GDPR

| Article | Feature | Endpoint |
|---------|---------|----------|
| Art. 20 | Data Portability | `POST /api/v1/gdpr/export` |
| Art. 17 | Right to Erasure | `POST /api/v1/gdpr/delete-account` |
| - | Consent Management | `PATCH /api/v1/gdpr/consent` |
| - | Cookie Preferences | `POST /api/v1/gdpr/cookie-consent` |

### Age Verification

All users must verify they are 18+ before using identity features.

```bash
POST /api/v1/gdpr/verify-age
{ "birthdate": "1990-01-15" }
```

---

## Environment Variables

```bash
# Core
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/actorhub
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-256-bit-secret-key
ENVIRONMENT=production

# External Services
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
ELEVENLABS_API_KEY=...
REPLICATE_API_TOKEN=...

# Monitoring
SENTRY_DSN=https://...@sentry.io/...

# Storage
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# Vector DB
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|------------|
| API Framework | FastAPI 0.104+ |
| Database | PostgreSQL 16 + pgvector |
| Cache/Queue | Redis 7 |
| Vector DB | Qdrant |
| Task Queue | Celery |
| ORM | SQLAlchemy 2.0 (async) |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | Next.js 14 |
| Styling | Tailwind CSS |
| Components | Radix UI |
| State | React Query + Zustand |

### AI/ML
| Component | Technology |
|-----------|------------|
| Face Recognition | InsightFace (buffalo_l) |
| Voice Cloning | ElevenLabs API |
| Image Generation | Replicate (LoRA) |

### DevOps
| Component | Technology |
|-----------|------------|
| Containers | Docker |
| CI/CD | GitHub Actions |
| Monitoring | Sentry + Prometheus |
| Logging | Structlog (JSON) |

---

## License

Proprietary - All rights reserved.

---

## Support

- Documentation: https://docs.actorhub.ai
- API Status: https://status.actorhub.ai
- Email: support@actorhub.ai

---

*Version: 1.0.0 | Last Updated: December 2024 | Status: Production Ready*
