# ActorHub.ai - System Documentation
## Digital Identity Protection & AI Actor Marketplace Platform

**Version:** 1.0
**Last Updated:** December 2024

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Features & Capabilities](#4-features--capabilities)
5. [API Reference](#5-api-reference)
6. [Database Schema](#6-database-schema)
7. [External Integrations](#7-external-integrations)
8. [Security Architecture](#8-security-architecture)
9. [Deployment & Infrastructure](#9-deployment--infrastructure)
10. [Configuration Reference](#10-configuration-reference)

---

## 1. Executive Summary

ActorHub.ai is an enterprise-grade platform for digital identity protection and AI actor marketplace. The platform enables individuals to:

- **Register and protect** their digital identity using facial recognition
- **Train AI models** (Actor Packs) based on their likeness
- **Monetize their identity** through a marketplace licensing system
- **Control usage** of their likeness in AI-generated content

### Core Value Propositions

| Stakeholder | Value |
|------------|-------|
| **Actors/Creators** | Monetize digital likeness, control AI usage, passive income |
| **Content Creators** | Legal access to AI-generated content with licensed identities |
| **Enterprises** | Compliant AI content generation with audit trails |

---

## 2. Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   Web    │  │  Mobile  │  │   API    │  │  Studio  │        │
│  │  (Next)  │  │   App    │  │ Clients  │  │   App    │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼─────────────┼─────────────┼───────────────┘
        │             │             │             │
        └─────────────┴──────┬──────┴─────────────┘
                             │
                    ┌────────▼────────┐
                    │     NGINX       │
                    │  Load Balancer  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌────────▼────────┐   ┌──────▼──────┐
│   FastAPI     │   │    Next.js      │   │   Celery    │
│   Backend     │   │    Frontend     │   │   Workers   │
│   (8000)      │   │    (3000)       │   │             │
└───────┬───────┘   └─────────────────┘   └──────┬──────┘
        │                                         │
        └─────────────────┬───────────────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
┌───▼───┐  ┌─────▼─────┐  ┌───▼───┐  ┌────▼────┐
│Postgres│  │   Redis   │  │ MinIO │  │ Qdrant  │
│ + vec  │  │  Cache    │  │  S3   │  │ Vectors │
└────────┘  └───────────┘  └───────┘  └─────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Next.js Frontend** | User interface, SSR, client-side routing |
| **FastAPI Backend** | REST API, business logic, authentication |
| **Celery Workers** | Async tasks: training, notifications, cleanup |
| **PostgreSQL** | Primary data store with pgvector extension |
| **Redis** | Caching, rate limiting, session management |
| **MinIO/S3** | File storage (images, audio, actor packs) |
| **Qdrant** | Vector similarity search for face embeddings |

---

## 3. Technology Stack

### Frontend (`apps/web/`)

| Category | Technology | Version |
|----------|-----------|---------|
| Framework | Next.js | 14.2.29 |
| Language | TypeScript | 5.x |
| UI Components | Radix UI | Latest |
| Styling | Tailwind CSS | 3.x |
| State Management | TanStack Query | 5.x |
| Forms | React Hook Form | 7.x |
| Animations | Framer Motion | 11.x |
| Testing | Vitest + Playwright | Latest |

### Backend (`apps/api/`)

| Category | Technology | Version |
|----------|-----------|---------|
| Framework | FastAPI | 0.115.6 |
| Language | Python | 3.11+ |
| ORM | SQLAlchemy | 2.0 |
| Database Driver | asyncpg | Latest |
| Validation | Pydantic | 2.x |
| Task Queue | Celery | 5.x |
| Face Recognition | InsightFace/ArcFace | Latest |

### Infrastructure

| Category | Technology |
|----------|-----------|
| Database | PostgreSQL 15 + pgvector |
| Cache | Redis 7 |
| Object Storage | MinIO / AWS S3 |
| Vector DB | Qdrant |
| Container | Docker + Docker Compose |
| Reverse Proxy | Nginx |
| Monitoring | Prometheus + Sentry |

---

## 4. Features & Capabilities

### 4.1 Identity Management

#### Registration Flow
```
1. User uploads selfie/ID photo
2. Liveness detection validates live capture
3. Face embedding extracted (512-dim ArcFace)
4. Duplicate check against existing identities
5. Identity created with PENDING status
6. Optional: Admin verification for VERIFIED status
```

#### Protection Levels

| Level | Features | Price |
|-------|----------|-------|
| **FREE** | Basic detection alerts, public gallery listing | $0/month |
| **PRO** | Real-time alerts, usage analytics, priority support | $29/month |
| **ENTERPRISE** | Custom restrictions, API access, legal support | $199/month |

#### Identity Status Flow
```
PENDING → VERIFIED → PROTECTED
                  ↘ SUSPENDED (if violations)
```

### 4.2 Actor Pack Training

#### Training Pipeline
```
1. User uploads 8-30 training images
2. Optional: Audio samples for voice cloning
3. Images validated (format, size, face detection)
4. Files uploaded to S3/MinIO
5. Training job queued in Celery
6. Replicate API trains LoRA model
7. ElevenLabs clones voice (if audio provided)
8. Actor Pack created with quality scores
9. User notified via email/push
```

#### Training Status
| Status | Description |
|--------|-------------|
| PENDING | Awaiting processing |
| QUEUED | In Celery queue |
| PROCESSING | Training in progress |
| COMPLETED | Ready for use |
| FAILED | Training failed (with error details) |

#### Quality Metrics
- **Quality Score**: Overall model quality (0-100)
- **Authenticity Score**: Likeness accuracy (0-100)
- **Consistency Score**: Output consistency (0-100)
- **Voice Quality**: Voice clone accuracy (0-100)

### 4.3 Marketplace

#### License Types

| Type | Description | Use Case |
|------|-------------|----------|
| SINGLE_USE | One-time generation | One-off projects |
| SUBSCRIPTION | Monthly access | Ongoing campaigns |
| UNLIMITED | Perpetual license | Enterprise use |
| CUSTOM | Negotiated terms | Special requirements |

#### Usage Types

| Type | Commercial | Attribution |
|------|------------|-------------|
| PERSONAL | No | No |
| COMMERCIAL | Yes | Optional |
| EDITORIAL | Yes (news) | Required |
| EDUCATIONAL | Limited | Required |

#### Pricing Model
```python
base_price = identity.base_license_price
tier_multiplier = {
    'SINGLE_USE': 1.0,
    'SUBSCRIPTION': 0.8,  # 20% discount
    'UNLIMITED': 3.0,     # 3x base
}
usage_multiplier = {
    'PERSONAL': 0.5,
    'COMMERCIAL': 1.5,
    'EDITORIAL': 1.0,
    'EDUCATIONAL': 0.3,
}
final_price = base_price * tier_multiplier * usage_multiplier
```

### 4.4 Content Generation

#### Generation Types

| Type | Technology | Output |
|------|------------|--------|
| Face | Replicate SDXL + LoRA | Images |
| Voice | ElevenLabs / XTTS | Audio |
| Motion | (Future) | Video |

#### Verification API
```http
POST /api/v1/identity/verify
Content-Type: application/json

{
  "image_url": "https://...",  // OR
  "image_base64": "data:image/..."
}

Response:
{
  "matches": [
    {
      "identity_id": "uuid",
      "display_name": "John Doe",
      "similarity": 0.92,
      "is_protected": true,
      "license_required": true
    }
  ],
  "processing_time_ms": 45
}
```

### 4.5 Creator Earnings

#### Revenue Flow
```
License Purchased ($100)
    ↓
Platform Fee (20%) → $20 to ActorHub
    ↓
Creator Earnings (80%) → $80 to Creator
    ↓
Holding Period (7 days)
    ↓
Available for Payout
    ↓
Minimum $50 reached → Payout via Stripe Connect
```

#### Payout Methods
- **Stripe Connect** (Primary) - Bank transfer
- **PayPal** - Alternative
- **Wire Transfer** - Enterprise

---

## 5. API Reference

### Base URL
```
Production: https://api.actorhub.ai/api/v1
Development: http://localhost:8000/api/v1
```

### Authentication

#### Cookie-Based (Web)
```http
POST /api/v1/users/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure123"
}

Response Headers:
Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Lax
Set-Cookie: refresh_token=<jwt>; HttpOnly; Secure; SameSite=Lax
```

#### API Key (Programmatic)
```http
GET /api/v1/identity/verify
X-API-Key: ak_live_xxxxxxxxxxxxx
```

### Endpoint Groups

#### Identity Endpoints (`/identity/`)
| Method | Path | Description |
|--------|------|-------------|
| POST | /register | Register new identity |
| GET | /gallery | Public identity gallery |
| POST | /verify | Verify faces in image |
| GET | /mine | List user's identities |
| GET | /{id} | Get identity details |
| PATCH | /{id} | Update identity |
| DELETE | /{id} | Soft delete identity |

#### Actor Pack Endpoints (`/actor-packs/`)
| Method | Path | Description |
|--------|------|-------------|
| POST | /train | Start training |
| GET | /status/{id} | Training status |
| GET | /download/{identity_id} | Download pack (licensed) |
| GET | /public | List public packs |

#### Marketplace Endpoints (`/marketplace/`)
| Method | Path | Description |
|--------|------|-------------|
| GET | /listings | Search listings |
| GET | /listings/{id} | Listing details |
| POST | /license/purchase | Purchase license |
| GET | /licenses/mine | User's licenses |

#### User Endpoints (`/users/`)
| Method | Path | Description |
|--------|------|-------------|
| POST | /register | Create account |
| POST | /login | Authenticate |
| GET | /me | Current user info |
| PATCH | /me | Update profile |
| POST | /api-keys | Create API key |
| GET | /earnings | Creator earnings |
| POST | /request-payout | Request payout |

#### Admin Endpoints (`/admin/`)
| Method | Path | Description |
|--------|------|-------------|
| GET | /dashboard | Admin stats |
| GET | /users | List all users |
| GET | /audit-logs | Audit trail |
| POST | /approve-identity/{id} | Approve identity |

### Rate Limits

| Tier | Requests/Minute | Burst |
|------|-----------------|-------|
| FREE | 60 | 10 |
| PRO | 300 | 50 |
| ENTERPRISE | 1000 | 100 |

---

## 6. Database Schema

### Core Models

#### User
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    display_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'USER',  -- USER, CREATOR, ADMIN
    tier VARCHAR(20) DEFAULT 'FREE',  -- FREE, PRO, ENTERPRISE
    is_active BOOLEAN DEFAULT TRUE,
    stripe_customer_id VARCHAR(100),
    stripe_connect_id VARCHAR(100),
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Identity
```sql
CREATE TABLE identities (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    bio TEXT,
    category VARCHAR(50),  -- ACTOR, MODEL, INFLUENCER, etc.
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, VERIFIED, PROTECTED, SUSPENDED
    protection_level VARCHAR(20) DEFAULT 'BASIC',
    profile_image_url TEXT,
    face_embedding VECTOR(512),  -- pgvector
    show_in_public_gallery BOOLEAN DEFAULT FALSE,
    allow_commercial_use BOOLEAN DEFAULT TRUE,
    allow_ai_training BOOLEAN DEFAULT TRUE,
    base_license_price DECIMAL(10,2) DEFAULT 50.00,
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP  -- Soft delete
);
```

#### ActorPack
```sql
CREATE TABLE actor_packs (
    id UUID PRIMARY KEY,
    identity_id UUID REFERENCES identities(id),
    name VARCHAR(255),
    training_status VARCHAR(20) DEFAULT 'PENDING',
    training_progress INTEGER DEFAULT 0,
    training_images_count INTEGER,
    training_audio_seconds INTEGER,
    quality_score DECIMAL(5,2),
    authenticity_score DECIMAL(5,2),
    consistency_score DECIMAL(5,2),
    components JSONB,  -- {face: true, voice: true, motion: false}
    s3_bucket VARCHAR(255),
    s3_key VARCHAR(255),
    file_size_bytes BIGINT,
    is_available BOOLEAN DEFAULT FALSE,
    total_downloads INTEGER DEFAULT 0,
    total_uses INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### License
```sql
CREATE TABLE licenses (
    id UUID PRIMARY KEY,
    identity_id UUID REFERENCES identities(id),
    licensee_id UUID REFERENCES users(id),
    license_type VARCHAR(20),  -- SINGLE_USE, SUBSCRIPTION, UNLIMITED
    usage_type VARCHAR(20),    -- PERSONAL, COMMERCIAL, EDITORIAL
    price_usd DECIMAL(10,2),
    payment_status VARCHAR(20) DEFAULT 'PENDING',
    is_active BOOLEAN DEFAULT TRUE,
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,
    current_uses INTEGER DEFAULT 0,
    max_uses INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Indexes
```sql
-- Performance indexes
CREATE INDEX idx_identities_user_id ON identities(user_id);
CREATE INDEX idx_identities_status ON identities(status);
CREATE INDEX idx_licenses_licensee_id ON licenses(licensee_id);
CREATE INDEX idx_licenses_identity_id ON licenses(identity_id);

-- Vector similarity search
CREATE INDEX idx_identities_embedding ON identities
    USING ivfflat (face_embedding vector_cosine_ops);
```

---

## 7. External Integrations

### 7.1 Stripe (Payments)

**Purpose:** Payment processing, subscriptions, creator payouts

**Configuration:**
```env
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_CONNECT_CLIENT_ID=ca_xxx
```

**Webhooks Handled:**
- `checkout.session.completed` - License purchase
- `customer.subscription.updated` - Subscription changes
- `invoice.paid` - Subscription renewal
- `account.updated` - Connect account status

### 7.2 Replicate (AI Models)

**Purpose:** Face generation, LoRA training

**Configuration:**
```env
REPLICATE_API_TOKEN=r8_xxx
```

**Models Used:**
- `stability-ai/sdxl` - Base image generation
- `lucataco/sdxl-lcm` - Fast generation
- Custom LoRA training for actor packs

### 7.3 ElevenLabs (Voice)

**Purpose:** Voice cloning and synthesis

**Configuration:**
```env
ELEVENLABS_API_KEY=sk_xxx
```

**Features:**
- Voice cloning from audio samples
- Text-to-speech generation
- Multiple voice models

### 7.4 SendGrid (Email)

**Purpose:** Transactional emails

**Configuration:**
```env
SENDGRID_API_KEY=SG.xxx
EMAIL_FROM=noreply@actorhub.ai
```

**Email Types:**
- Welcome emails
- Password reset
- Training completion
- License purchase confirmation
- Payout notifications

### 7.5 Qdrant (Vector Search)

**Purpose:** Face embedding similarity search

**Configuration:**
```env
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=face_embeddings
```

**Operations:**
- Store face embeddings (512-dim)
- Similarity search (cosine)
- Duplicate detection

---

## 8. Security Architecture

### 8.1 Authentication

#### JWT Configuration
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
JWT_ALGORITHM = "HS256"
```

#### Cookie Security
```python
cookie_settings = {
    "httponly": True,
    "secure": True,  # HTTPS only
    "samesite": "lax",
    "max_age": 60 * 60 * 24 * 7  # 7 days
}
```

### 8.2 Rate Limiting

```python
# Redis-backed rate limiting
rate_limits = {
    "FREE": "60/minute",
    "PRO": "300/minute",
    "ENTERPRISE": "1000/minute",
    "login": "5/minute",  # Stricter for auth
}
```

### 8.3 Security Headers

```python
headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; ...",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
```

### 8.4 Input Validation

- Request body size limits (10MB regular, 500MB uploads)
- File type validation (MIME + magic bytes)
- SQL injection prevention (parameterized queries)
- XSS prevention (input sanitization)
- Path traversal protection

### 8.5 GDPR Compliance

```python
gdpr_features = {
    "consent_management": True,  # Marketing, analytics, 3rd party
    "data_export": True,         # JSON export of user data
    "account_deletion": True,    # Full data removal
    "retention_periods": True,   # Automated data cleanup
}
```

---

## 9. Deployment & Infrastructure

### 9.1 Docker Compose

```yaml
services:
  api:
    build: ./apps/api
    ports: ["8000:8000"]
    depends_on: [postgres, redis, minio]

  web:
    build: ./apps/web
    ports: ["3000:3000"]

  worker:
    build: ./apps/worker
    depends_on: [redis, postgres]

  postgres:
    image: pgvector/pgvector:pg15
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine

  minio:
    image: minio/minio
    volumes: [minio_data:/data]

  qdrant:
    image: qdrant/qdrant
    volumes: [qdrant_data:/qdrant/storage]
```

### 9.2 Production Nginx

```nginx
# File upload limits
client_max_body_size 500M;

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

# SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:...;

# Security headers
add_header Strict-Transport-Security "max-age=31536000";
add_header X-Frame-Options "DENY";
```

### 9.3 Health Checks

| Endpoint | Purpose |
|----------|---------|
| `/health` | Basic liveness |
| `/health/ready` | Database + Redis status |
| `/health/resilience` | Circuit breaker status |

---

## 10. Configuration Reference

### Environment Variables

#### Required
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/actorhub

# Redis
REDIS_URL=redis://localhost:6379

# Security
JWT_SECRET_KEY=<random-256-bit-key>
ENCRYPTION_KEY=<random-256-bit-key>

# Stripe
STRIPE_SECRET_KEY=sk_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# AI Services
REPLICATE_API_TOKEN=r8_xxx
ELEVENLABS_API_KEY=sk_xxx
```

#### Optional
```env
# Feature Flags
ENABLE_MARKETPLACE=true
ENABLE_ACTOR_PACKS=true
ENABLE_VOICE_CLONING=true
ENABLE_BLOCKCHAIN=false

# Thresholds
FACE_SIMILARITY_THRESHOLD=0.80
FACE_DUPLICATE_THRESHOLD=0.85

# Payouts
PLATFORM_FEE_PERCENT=20
MINIMUM_PAYOUT_USD=50
PAYOUT_HOLDING_DAYS=7

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
```

---

## Appendix A: Code Metrics

| Metric | Value |
|--------|-------|
| Total Lines (Models/Services) | ~7,000 |
| API Endpoints | ~102 |
| Database Models | 12+ |
| Service Methods | 180+ |
| External Integrations | 7+ |

---

## Appendix B: Directory Structure

```
ActorHub.ai/
├── apps/
│   ├── api/                 # FastAPI Backend
│   │   ├── app/
│   │   │   ├── api/v1/      # API endpoints
│   │   │   ├── core/        # Config, security, database
│   │   │   ├── middleware/  # Security, logging, rate limit
│   │   │   ├── models/      # SQLAlchemy models
│   │   │   ├── schemas/     # Pydantic schemas
│   │   │   └── services/    # Business logic
│   │   ├── alembic/         # Database migrations
│   │   └── tests/           # API tests
│   │
│   ├── web/                 # Next.js Frontend
│   │   ├── src/
│   │   │   ├── app/         # App router pages
│   │   │   ├── components/  # React components
│   │   │   ├── hooks/       # Custom hooks
│   │   │   ├── lib/         # Utilities, API client
│   │   │   └── store/       # State management
│   │   └── e2e/             # Playwright tests
│   │
│   ├── worker/              # Celery Workers
│   │   └── tasks/           # Async task definitions
│   │
│   └── studio/              # Desktop App (Electron)
│
├── nginx/                   # Nginx configuration
├── infrastructure/          # Monitoring, alerts
├── docker-compose.yml       # Development setup
└── docker-compose.prod.yml  # Production setup
```

---

**Document maintained by:** ActorHub.ai Engineering Team
**Last review:** December 2024
