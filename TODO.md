# ActorHub.ai - Todo List

> Generated from comprehensive security audit on 2025-12-17
> Total issues found: 113 (Routers: 83, Models: 18, Services: 12)

---

## P0 - Critical (Must fix before production)

### Security Vulnerabilities - Immediate Action Required

- [x] **Clerk webhook signature verification not implemented**
  - File: `apps/api/app/api/v1/endpoints/webhooks.py:184`
  - Risk: Any attacker can forge Clerk webhooks, create fake users, manipulate data
  - Fix: Use svix library to verify webhook signatures
  - Status: FIXED

- [x] **Timing attack on password reset token**
  - File: `apps/api/app/api/v1/endpoints/auth_extended.py:102`
  - Risk: Attackers can enumerate valid reset tokens via timing side-channel
  - Fix: Use `secrets.compare_digest()` for constant-time comparison
  - Status: FIXED

- [x] **Timing attack on email verification token**
  - File: `apps/api/app/api/v1/endpoints/auth_extended.py:165`
  - Risk: Attackers can enumerate valid verification tokens
  - Fix: Use `secrets.compare_digest()` for constant-time comparison
  - Status: FIXED

- [x] **SSRF vulnerability in face URL detection**
  - File: `apps/api/app/api/v1/endpoints/identity.py:181`
  - Risk: Attackers can make server fetch internal resources, scan internal network
  - Fix: Add URL domain whitelist, validate scheme
  - Status: FIXED

- [x] **DEBUG flag exposed in health endpoint**
  - File: `apps/api/app/api/v1/endpoints/health.py:19`
  - Risk: Leaks environment information to attackers
  - Fix: Remove `debug` from response
  - Status: FIXED

- [x] **Rate limiting bypass for localhost**
  - File: `apps/api/app/middleware/rate_limit.py:232`
  - Risk: Development blocked by rate limits
  - Fix: Add localhost IP check at start of dispatch
  - Status: FIXED

---

## P1 - High Priority (This Week)

### Async/Performance Issues

- [x] **Synchronous Qdrant calls blocking event loop**
  - File: `apps/api/app/services/face_recognition.py`
  - Risk: Server becomes unresponsive under load, high latency
  - Fix: Used `run_in_executor()` for all Qdrant calls
  - Status: FIXED

- [x] **Synchronous boto3 calls blocking event loop**
  - File: `apps/api/app/services/storage.py`
  - Risk: S3 operations block entire server, poor performance
  - Fix: Used `run_in_executor()` with functools.partial for all boto3 calls
  - Status: FIXED

### Security Improvements

- [x] **No rate limiting on token refresh endpoint**
  - File: `apps/api/app/api/v1/endpoints/users.py:103`
  - Risk: Token refresh bomb attack, resource exhaustion
  - Fix: Added `@limiter.limit("5/minute")` decorator
  - Status: FIXED

- [x] **Arbitrary field modification via setattr() in identity**
  - File: `apps/api/app/api/v1/endpoints/identity.py:347`
  - Risk: Attackers can modify sensitive fields like `protection_level`, `user_id`
  - Fix: Added ALLOWED_IDENTITY_UPDATE_FIELDS allowlist
  - Status: FIXED

- [x] **Arbitrary field modification via setattr() in users**
  - File: `apps/api/app/api/v1/endpoints/users.py:152`
  - Risk: Attackers can escalate privileges by modifying `role`, `tier`
  - Fix: Added ALLOWED_USER_UPDATE_FIELDS allowlist
  - Status: FIXED

### Database Indexes

- [x] **Missing indexes on User model**
  - File: `apps/api/app/models/user.py`
  - Risk: Slow queries at scale, poor performance
  - Fix: Created Alembic migration with all indexes
  - Status: FIXED - Migration file created at `alembic/versions/20251217_add_missing_indexes.py`

- [x] **Missing index on ApiKey.user_id**
  - Status: FIXED - Included in migration

- [x] **Missing indexes on UsageLog**
  - Status: FIXED - Included in migration

- [x] **Missing indexes on License**
  - Status: FIXED - Included in migration

- [x] **Missing indexes on Transaction**
  - Status: FIXED - Included in migration

---

## P2 - Medium Priority (This Sprint)

### Data Model Improvements

- [x] **ActorPack.training_status should be Enum, not String**
  - File: `apps/api/app/models/identity.py`
  - Risk: Data inconsistency, invalid status values possible
  - Fix: Changed to `Column(Enum(TrainingStatus), default=TrainingStatus.PENDING)`
  - Status: FIXED

- [x] **Transaction.type should be Enum, not String**
  - File: `apps/api/app/models/marketplace.py`
  - Risk: Invalid transaction types, data inconsistency
  - Fix: Created TransactionType enum and updated model
  - Status: FIXED

- [x] **Listing.category should be Enum**
  - File: `apps/api/app/models/marketplace.py`
  - Risk: Inconsistent category names
  - Fix: Created ListingCategory enum and updated model
  - Status: FIXED

### Security & Configuration

- [x] **AWS credentials hardcoded in storage service**
  - File: `apps/api/app/services/storage.py`
  - Risk: Credentials in code, rotation difficult
  - Fix: Made credentials optional, supports IAM roles in production
  - Status: FIXED

- [x] **Email sending not implemented**
  - File: `apps/api/app/api/v1/endpoints/auth_extended.py`
  - Risk: Password reset and verification emails not sent
  - Fix: Implemented with SendGrid API, added configuration to settings
  - Status: FIXED

- [x] **Webhook idempotency not handled**
  - File: `apps/api/app/api/v1/endpoints/webhooks.py`
  - Risk: Same webhook processed multiple times, duplicate transactions
  - Fix: Added `check_idempotency()` function for Stripe and Clerk webhooks
  - Status: FIXED

---

## P3 - Low Priority (Technical Debt)

### Incomplete Implementations

- [x] **Quality assessment returns mock data**
  - File: `apps/api/app/services/training.py`
  - Risk: Inaccurate quality scores, poor user experience
  - Fix: Implemented real quality assessment using embedding similarity
  - Status: FIXED - Uses cosine similarity for consistency scoring

- [x] **LoRA training not implemented**
  - File: `apps/api/app/services/training.py`
  - Risk: Feature not working
  - Fix: Implemented with Replicate API (ostris/flux-dev-lora-trainer)
  - Status: FIXED - Full integration with S3 upload and training polling

- [x] **Motion extraction not implemented**
  - File: `apps/api/app/services/training.py`
  - Risk: Feature returns placeholder
  - Fix: Implemented with MediaPipe pose estimation
  - Status: FIXED - Extracts 33-point pose landmarks from video

### Code Quality

- [x] **UsageLog relationships incomplete**
  - File: `apps/api/app/models/identity.py`
  - Risk: Missing relationships for actor_pack, api_key, license
  - Fix: Added all missing relationships
  - Status: FIXED

- [x] **Add composite indexes for analytics**
  - File: `apps/api/app/models/identity.py`
  - Risk: Slow analytics queries
  - Fix: Included in migration file
  - Status: FIXED

- [x] **Remove mock mode fallbacks in production**
  - Files: `face_recognition.py`
  - Risk: Mock data served in production
  - Fix: Mock mode now requires explicit `FACE_RECOGNITION_MOCK=true` env var
  - Status: FIXED

---

## Router Issues Summary (83 Total)

| File | Error Handling | Input Validation | Security |
|------|----------------|------------------|----------|
| actor_packs.py | 4 | 3 | 3 |
| auth_extended.py | 3 | 4 | 6 |
| gdpr.py | 4 | 3 | 2 |
| health.py | 2 | 0 | 2 |
| identity.py | 3 | 4 | 4 |
| marketplace.py | 3 | 5 | 4 |
| users.py | 2 | 3 | 3 |
| webhooks.py | 5 | 4 | 7 |
| **TOTAL** | **26** | **26** | **31** |

---

## Dependencies Added

```txt
# Already in requirements.txt
svix>=1.80.0          # Clerk webhook verification
sendgrid>=6.0.0       # Email sending (add if not present)
```

---

## Migration Notes

Database migration file created: `apps/api/alembic/versions/20251217_add_missing_indexes.py`

To apply migration:
```bash
cd apps/api
alembic upgrade head
```

**Note:** Update `down_revision` in the migration file to point to your latest revision before running.

---

## Configuration Added

Add these to your `.env` file:

```env
# Email (SendGrid)
SENDGRID_API_KEY=your_sendgrid_api_key
EMAIL_FROM=noreply@actorhub.ai
EMAIL_FROM_NAME=ActorHub.ai

# Clerk
CLERK_WEBHOOK_SECRET=your_clerk_webhook_secret
```

---

## Progress Tracking

- [x] P0 completed: 6/6 (100%)
- [x] P1 completed: 10/10 (100%)
- [x] P2 completed: 6/6 (100%)
- [x] P3 completed: 6/6 (100%)

**Total: 28/28 tasks completed (100%)**

### Additional Improvements (2025-12-18)

1. **New Database Tables Added**
   - `notifications` - User notification system
   - `audit_logs` - Security audit trail
   - `webhook_events` - Webhook idempotency
   - `subscriptions` - Billing subscriptions
   - `payouts` - Creator payouts

2. **New API Endpoints Added**
   - `/api/v1/notifications` - Notification management
   - `/api/v1/subscriptions` - Subscription & billing
   - `/api/v1/admin` - Admin dashboard & management

3. **Security Improvements**
   - `require_admin` dependency for admin routes
   - Proper role-based access control

4. **Comprehensive Tests Added**
   - `test_notifications.py` - Notification endpoint tests
   - `test_admin.py` - Admin endpoint tests
   - `test_subscriptions.py` - Subscription endpoint tests
   - `test_training_service.py` - Training service unit tests

5. **Dependencies Updated**
   - Added `replicate==0.25.1` for LoRA training
   - Added `mediapipe==0.10.9` for motion capture
   - Added `sendgrid==6.11.0` for email

---

*Last updated: 2025-12-18*
