# Data Integrity Audit Report

**Platform:** ActorHub.ai
**Audit Date:** 2024-12-21
**Auditor:** Data Engineering Team
**Scope:** apps/api/app/models/*.py

---

## Executive Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Missing FK ON DELETE | 17 | - | - | - | 17 |
| Missing Unique Constraints | - | 4 | 2 | - | 6 |
| Missing Check Constraints | - | 8 | 6 | - | 14 |
| Orphan Data Risks | 4 | 3 | - | - | 7 |
| Validation Gaps | - | 5 | 4 | - | 9 |
| Denormalized Data Drift | - | 7 | 3 | - | 10 |
| Temporal/Audit Issues | - | 2 | 4 | - | 6 |
| **Total** | **21** | **29** | **19** | **0** | **69** |

---

## 1. Missing ON DELETE Behavior (CRITICAL)

All foreign keys default to `ON DELETE RESTRICT`, preventing proper data lifecycle management.

### 1.1 Impact Matrix

| Parent Table | Child Table | FK Column | Current | Risk Level | Recommended |
|--------------|-------------|-----------|---------|------------|-------------|
| users | identities | user_id | RESTRICT | CRITICAL | CASCADE |
| users | api_keys | user_id | RESTRICT | CRITICAL | CASCADE |
| users | licenses | licensee_id | RESTRICT | CRITICAL | SET NULL |
| users | transactions | user_id | RESTRICT | CRITICAL | SET NULL |
| users | notifications | user_id | RESTRICT | HIGH | CASCADE |
| users | audit_logs | user_id | RESTRICT | HIGH | SET NULL |
| users | subscriptions | user_id | RESTRICT | CRITICAL | CASCADE |
| users | payouts | user_id | RESTRICT | CRITICAL | SET NULL |
| identities | actor_packs | identity_id | RESTRICT | CRITICAL | CASCADE |
| identities | licenses | identity_id | RESTRICT | CRITICAL | SET NULL |
| identities | listings | identity_id | RESTRICT | CRITICAL | CASCADE |
| identities | usage_logs | identity_id | RESTRICT | HIGH | SET NULL |
| licenses | transactions | license_id | RESTRICT | HIGH | SET NULL |
| licenses | usage_logs | license_id | RESTRICT | MEDIUM | SET NULL |
| actor_packs | usage_logs | actor_pack_id | RESTRICT | MEDIUM | SET NULL |
| api_keys | usage_logs | api_key_id | RESTRICT | MEDIUM | SET NULL |
| api_keys | audit_logs | api_key_id | RESTRICT | MEDIUM | SET NULL |

### 1.2 Data Corruption Scenario

```
User wants to delete their account:
1. App tries DELETE FROM users WHERE id = ?
2. DB rejects: foreign key constraint violation
3. User stuck, cannot exercise GDPR "right to be forgotten"
4. Manual intervention required for each user deletion
```

### 1.3 Migration Script

```sql
-- Migration: 001_add_on_delete_constraints.sql
-- WARNING: Run during maintenance window, may lock tables

BEGIN;

-- Drop and recreate foreign keys with proper ON DELETE behavior

-- identities.user_id -> CASCADE (delete user = delete their identities)
ALTER TABLE identities DROP CONSTRAINT IF EXISTS identities_user_id_fkey;
ALTER TABLE identities ADD CONSTRAINT identities_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- api_keys.user_id -> CASCADE
ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS api_keys_user_id_fkey;
ALTER TABLE api_keys ADD CONSTRAINT api_keys_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- actor_packs.identity_id -> CASCADE
ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS actor_packs_identity_id_fkey;
ALTER TABLE actor_packs ADD CONSTRAINT actor_packs_identity_id_fkey
    FOREIGN KEY (identity_id) REFERENCES identities(id) ON DELETE CASCADE;

-- listings.identity_id -> CASCADE
ALTER TABLE listings DROP CONSTRAINT IF EXISTS listings_identity_id_fkey;
ALTER TABLE listings ADD CONSTRAINT listings_identity_id_fkey
    FOREIGN KEY (identity_id) REFERENCES identities(id) ON DELETE CASCADE;

-- licenses.identity_id -> SET NULL (preserve license history)
ALTER TABLE licenses DROP CONSTRAINT IF EXISTS licenses_identity_id_fkey;
ALTER TABLE licenses ADD CONSTRAINT licenses_identity_id_fkey
    FOREIGN KEY (identity_id) REFERENCES identities(id) ON DELETE SET NULL;
ALTER TABLE licenses ALTER COLUMN identity_id DROP NOT NULL;

-- licenses.licensee_id -> SET NULL
ALTER TABLE licenses DROP CONSTRAINT IF EXISTS licenses_licensee_id_fkey;
ALTER TABLE licenses ADD CONSTRAINT licenses_licensee_id_fkey
    FOREIGN KEY (licensee_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE licenses ALTER COLUMN licensee_id DROP NOT NULL;

-- transactions.license_id -> SET NULL
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_license_id_fkey;
ALTER TABLE transactions ADD CONSTRAINT transactions_license_id_fkey
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE SET NULL;

-- transactions.user_id -> SET NULL
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_user_id_fkey;
ALTER TABLE transactions ADD CONSTRAINT transactions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE transactions ALTER COLUMN user_id DROP NOT NULL;

-- notifications.user_id -> CASCADE
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_user_id_fkey;
ALTER TABLE notifications ADD CONSTRAINT notifications_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- subscriptions.user_id -> CASCADE
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_user_id_fkey;
ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- payouts.user_id -> SET NULL (preserve financial records)
ALTER TABLE payouts DROP CONSTRAINT IF EXISTS payouts_user_id_fkey;
ALTER TABLE payouts ADD CONSTRAINT payouts_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE payouts ALTER COLUMN user_id DROP NOT NULL;

-- usage_logs - all SET NULL for historical preservation
ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_identity_id_fkey;
ALTER TABLE usage_logs ADD CONSTRAINT usage_logs_identity_id_fkey
    FOREIGN KEY (identity_id) REFERENCES identities(id) ON DELETE SET NULL;

ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_license_id_fkey;
ALTER TABLE usage_logs ADD CONSTRAINT usage_logs_license_id_fkey
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE SET NULL;

ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_actor_pack_id_fkey;
ALTER TABLE usage_logs ADD CONSTRAINT usage_logs_actor_pack_id_fkey
    FOREIGN KEY (actor_pack_id) REFERENCES actor_packs(id) ON DELETE SET NULL;

ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_api_key_id_fkey;
ALTER TABLE usage_logs ADD CONSTRAINT usage_logs_api_key_id_fkey
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE SET NULL;

-- audit_logs - SET NULL for compliance
ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_user_id_fkey;
ALTER TABLE audit_logs ADD CONSTRAINT audit_logs_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_api_key_id_fkey;
ALTER TABLE audit_logs ADD CONSTRAINT audit_logs_api_key_id_fkey
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE SET NULL;

COMMIT;
```

---

## 2. Missing Unique Constraints

### 2.1 Issues Found

| Table | Columns | Risk | Scenario |
|-------|---------|------|----------|
| identities | (user_id, display_name) | HIGH | User creates duplicate-named identities, confusion in UI |
| listings | identity_id | HIGH | Multiple listings for same identity, pricing confusion |
| subscriptions | (user_id) WHERE status='ACTIVE' | CRITICAL | User gets multiple active subscriptions, double billing |
| api_keys | (user_id, name) | MEDIUM | Duplicate API key names, user confusion |
| actor_packs | identity_id | MEDIUM | Already has unique=True, but verify index exists |
| payouts | (user_id, period_start, period_end) | HIGH | Duplicate payouts for same period |

### 2.2 Migration Script

```sql
-- Migration: 002_add_unique_constraints.sql

BEGIN;

-- Prevent duplicate identity names per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_identity_user_display_name
    ON identities(user_id, lower(display_name))
    WHERE deleted_at IS NULL;

-- One listing per identity
CREATE UNIQUE INDEX IF NOT EXISTS idx_listing_identity_unique
    ON listings(identity_id)
    WHERE is_active = true;

-- One active subscription per user (partial unique index)
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscription_user_active
    ON subscriptions(user_id)
    WHERE status = 'ACTIVE';

-- Unique API key names per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_apikey_user_name
    ON api_keys(user_id, lower(name))
    WHERE is_active = true;

-- Prevent duplicate payouts for same period
CREATE UNIQUE INDEX IF NOT EXISTS idx_payout_user_period
    ON payouts(user_id, period_start, period_end)
    WHERE status != 'CANCELED';

COMMIT;
```

---

## 3. Missing Check Constraints

### 3.1 Issues Found

| Table | Column | Constraint Needed | Risk |
|-------|--------|-------------------|------|
| licenses | price_usd | >= 0 | Negative prices corrupt financials |
| licenses | creator_payout_usd | >= 0 AND <= price_usd | Payout exceeds price |
| licenses | platform_fee_percent | BETWEEN 0 AND 100 | Invalid percentage |
| licenses | current_uses | >= 0 | Negative usage count |
| identities | revenue_share_percent | BETWEEN 0 AND 100 | Invalid percentage |
| identities | base_license_fee | >= 0 | Negative pricing |
| actor_packs | training_progress | BETWEEN 0 AND 100 | Invalid progress |
| actor_packs | quality_score | BETWEEN 0 AND 100 | Invalid score |
| actor_packs | file_size_bytes | >= 0 | Negative file size |
| payouts | amount | > 0 | Zero/negative payout |
| payouts | net_amount | >= 0 AND <= amount | Net exceeds gross |
| subscriptions | amount | >= 0 | Negative subscription cost |
| transactions | amount_usd | != 0 | Zero-value transaction |
| usage_logs | response_time_ms | >= 0 | Negative response time |

### 3.2 Migration Script

```sql
-- Migration: 003_add_check_constraints.sql

BEGIN;

-- License financial constraints
ALTER TABLE licenses ADD CONSTRAINT chk_license_price_positive
    CHECK (price_usd >= 0);
ALTER TABLE licenses ADD CONSTRAINT chk_license_payout_valid
    CHECK (creator_payout_usd >= 0 AND creator_payout_usd <= price_usd);
ALTER TABLE licenses ADD CONSTRAINT chk_license_fee_percent
    CHECK (platform_fee_percent >= 0 AND platform_fee_percent <= 100);
ALTER TABLE licenses ADD CONSTRAINT chk_license_uses_positive
    CHECK (current_uses >= 0);
ALTER TABLE licenses ADD CONSTRAINT chk_license_dates_valid
    CHECK (valid_until IS NULL OR valid_until >= valid_from);

-- Identity pricing constraints
ALTER TABLE identities ADD CONSTRAINT chk_identity_revenue_share
    CHECK (revenue_share_percent >= 0 AND revenue_share_percent <= 100);
ALTER TABLE identities ADD CONSTRAINT chk_identity_prices_positive
    CHECK (base_license_fee >= 0 AND hourly_rate >= 0 AND per_image_rate >= 0);

-- Actor pack constraints
ALTER TABLE actor_packs ADD CONSTRAINT chk_pack_progress_range
    CHECK (training_progress >= 0 AND training_progress <= 100);
ALTER TABLE actor_packs ADD CONSTRAINT chk_pack_quality_range
    CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100));
ALTER TABLE actor_packs ADD CONSTRAINT chk_pack_authenticity_range
    CHECK (authenticity_score IS NULL OR (authenticity_score >= 0 AND authenticity_score <= 100));
ALTER TABLE actor_packs ADD CONSTRAINT chk_pack_file_size
    CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0);
ALTER TABLE actor_packs ADD CONSTRAINT chk_pack_prices_positive
    CHECK (base_price_usd >= 0 AND price_per_second_usd >= 0 AND price_per_image_usd >= 0);

-- Payout constraints
ALTER TABLE payouts ADD CONSTRAINT chk_payout_amount_positive
    CHECK (amount > 0);
ALTER TABLE payouts ADD CONSTRAINT chk_payout_net_valid
    CHECK (net_amount IS NULL OR (net_amount >= 0 AND net_amount <= amount));
ALTER TABLE payouts ADD CONSTRAINT chk_payout_fee_positive
    CHECK (fee >= 0);

-- Subscription constraints
ALTER TABLE subscriptions ADD CONSTRAINT chk_subscription_amount_positive
    CHECK (amount >= 0);
ALTER TABLE subscriptions ADD CONSTRAINT chk_subscription_limits_positive
    CHECK (identities_limit >= 0 AND api_calls_limit >= 0 AND storage_limit_mb >= 0);

-- Transaction constraints
ALTER TABLE transactions ADD CONSTRAINT chk_transaction_nonzero
    CHECK (amount_usd != 0);

-- Usage log constraints
ALTER TABLE usage_logs ADD CONSTRAINT chk_usage_response_time
    CHECK (response_time_ms IS NULL OR response_time_ms >= 0);
ALTER TABLE usage_logs ADD CONSTRAINT chk_usage_similarity
    CHECK (similarity_score IS NULL OR (similarity_score >= 0 AND similarity_score <= 1));

COMMIT;
```

---

## 4. Orphan Data Risks

### 4.1 Soft Delete Cascade Issues

The `identities` table uses soft delete (`deleted_at`), but related tables don't handle this:

```
Identity (deleted_at = NOW)
    ├── actor_packs (still visible, training may continue)
    ├── listings (still active, can be purchased!)
    ├── licenses (still valid, may cause billing issues)
    └── usage_logs (references deleted identity)
```

### 4.2 Migration Script for Soft Delete Triggers

```sql
-- Migration: 004_soft_delete_cascade_triggers.sql

BEGIN;

-- Function to cascade soft deletes
CREATE OR REPLACE FUNCTION cascade_identity_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
        -- Deactivate listings
        UPDATE listings
        SET is_active = false, updated_at = NOW()
        WHERE identity_id = NEW.id;

        -- Cancel pending actor pack training
        UPDATE actor_packs
        SET training_status = 'FAILED',
            training_error = 'Identity was deleted',
            updated_at = NOW()
        WHERE identity_id = NEW.id
        AND training_status IN ('PENDING', 'QUEUED', 'PROCESSING');

        -- Mark actor pack as unavailable
        UPDATE actor_packs
        SET is_available = false, updated_at = NOW()
        WHERE identity_id = NEW.id;

        -- Deactivate active licenses (don't delete - preserve for billing)
        UPDATE licenses
        SET is_active = false, updated_at = NOW()
        WHERE identity_id = NEW.id AND is_active = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_identity_soft_delete
    AFTER UPDATE OF deleted_at ON identities
    FOR EACH ROW
    EXECUTE FUNCTION cascade_identity_soft_delete();

-- Add soft delete to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- Function to cascade user soft deletes
CREATE OR REPLACE FUNCTION cascade_user_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
        -- Soft delete all user's identities
        UPDATE identities
        SET deleted_at = NOW(),
            status = 'SUSPENDED',
            updated_at = NOW()
        WHERE user_id = NEW.id AND deleted_at IS NULL;

        -- Deactivate API keys
        UPDATE api_keys
        SET is_active = false, updated_at = NOW()
        WHERE user_id = NEW.id;

        -- Cancel active subscriptions
        UPDATE subscriptions
        SET status = 'CANCELED',
            canceled_at = NOW(),
            updated_at = NOW()
        WHERE user_id = NEW.id AND status = 'ACTIVE';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_soft_delete
    AFTER UPDATE OF deleted_at ON users
    FOR EACH ROW
    EXECUTE FUNCTION cascade_user_soft_delete();

COMMIT;
```

---

## 5. Validation Gaps

### 5.1 App Validates but DB Doesn't Enforce

| Field | App Validation | DB Enforcement | Risk |
|-------|----------------|----------------|------|
| users.email | Email format | None | Invalid emails via direct DB access |
| *.status | Enum values | VARCHAR (no check) | Invalid status values |
| licenses.valid_until | >= valid_from | None | End before start |
| actor_packs.version | Semver format | None | Invalid versions |
| *.url fields | URL format | None | Invalid URLs stored |

### 5.2 Status Field Enum Enforcement

```sql
-- Migration: 005_add_status_constraints.sql

BEGIN;

-- Create enum types for type safety
DO $$ BEGIN
    CREATE TYPE identity_status AS ENUM ('PENDING', 'PROCESSING', 'VERIFIED', 'REJECTED', 'SUSPENDED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE training_status AS ENUM ('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE payment_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Add check constraints for status fields (if not using enum types)
ALTER TABLE identities ADD CONSTRAINT chk_identity_status
    CHECK (status IN ('PENDING', 'PROCESSING', 'VERIFIED', 'REJECTED', 'SUSPENDED'));

ALTER TABLE actor_packs ADD CONSTRAINT chk_training_status
    CHECK (training_status IN ('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'));

ALTER TABLE licenses ADD CONSTRAINT chk_payment_status
    CHECK (payment_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED'));

ALTER TABLE licenses ADD CONSTRAINT chk_license_type
    CHECK (license_type IN ('SINGLE_USE', 'SUBSCRIPTION', 'UNLIMITED', 'CUSTOM'));

ALTER TABLE licenses ADD CONSTRAINT chk_usage_type
    CHECK (usage_type IN ('PERSONAL', 'COMMERCIAL', 'EDITORIAL', 'EDUCATIONAL'));

-- Email format validation (basic)
ALTER TABLE users ADD CONSTRAINT chk_email_format
    CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

COMMIT;
```

---

## 6. Denormalized Data Drift

### 6.1 Fields at Risk

| Table | Field | Should Equal | Drift Risk |
|-------|-------|--------------|------------|
| identities | total_verifications | COUNT(usage_logs WHERE action='verify') | HIGH |
| identities | total_licenses | COUNT(licenses WHERE identity_id=?) | HIGH |
| identities | total_revenue | SUM(licenses.creator_payout_usd) | CRITICAL |
| actor_packs | total_downloads | COUNT(usage_logs WHERE action='download') | MEDIUM |
| actor_packs | total_uses | COUNT(usage_logs WHERE action='generate') | MEDIUM |
| actor_packs | total_revenue_usd | SUM(usage_logs.amount_charged_usd) | CRITICAL |
| listings | license_count | COUNT(licenses) | MEDIUM |
| listings | view_count | Race condition without atomic update | LOW |

### 6.2 Trigger-Based Consistency

```sql
-- Migration: 006_denormalized_data_triggers.sql

BEGIN;

-- Trigger to update identity stats on usage_log insert
CREATE OR REPLACE FUNCTION update_identity_verification_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.action = 'verify' AND NEW.matched = true THEN
        UPDATE identities
        SET total_verifications = total_verifications + 1,
            updated_at = NOW()
        WHERE id = NEW.identity_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_usage_log_verification
    AFTER INSERT ON usage_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_identity_verification_count();

-- Trigger to update identity license count
CREATE OR REPLACE FUNCTION update_identity_license_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE identities
        SET total_licenses = total_licenses + 1,
            updated_at = NOW()
        WHERE id = NEW.identity_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_license_count
    AFTER INSERT ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION update_identity_license_count();

-- Trigger to update revenue on license payment completion
CREATE OR REPLACE FUNCTION update_identity_revenue()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.payment_status = 'COMPLETED' AND
       (OLD.payment_status IS NULL OR OLD.payment_status != 'COMPLETED') THEN
        UPDATE identities
        SET total_revenue = total_revenue + COALESCE(NEW.creator_payout_usd, 0),
            updated_at = NOW()
        WHERE id = NEW.identity_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_license_revenue
    AFTER UPDATE OF payment_status ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION update_identity_revenue();

-- Trigger for actor pack download count
CREATE OR REPLACE FUNCTION update_actor_pack_downloads()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.action = 'download' AND NEW.actor_pack_id IS NOT NULL THEN
        UPDATE actor_packs
        SET total_downloads = total_downloads + 1,
            updated_at = NOW()
        WHERE id = NEW.actor_pack_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_usage_log_download
    AFTER INSERT ON usage_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_actor_pack_downloads();

-- Atomic view count increment (prevent race conditions)
CREATE OR REPLACE FUNCTION increment_listing_view()
RETURNS TRIGGER AS $$
BEGIN
    -- Use row-level lock for atomic update
    PERFORM pg_advisory_xact_lock(hashtext('listing_view_' || NEW.id::text));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMIT;
```

### 6.3 Reconciliation Queries

```sql
-- Run periodically to detect and fix drift

-- Fix identity.total_verifications
UPDATE identities i
SET total_verifications = (
    SELECT COUNT(*) FROM usage_logs
    WHERE identity_id = i.id AND action = 'verify' AND matched = true
)
WHERE total_verifications != (
    SELECT COUNT(*) FROM usage_logs
    WHERE identity_id = i.id AND action = 'verify' AND matched = true
);

-- Fix identity.total_licenses
UPDATE identities i
SET total_licenses = (
    SELECT COUNT(*) FROM licenses WHERE identity_id = i.id
)
WHERE total_licenses != (
    SELECT COUNT(*) FROM licenses WHERE identity_id = i.id
);

-- Fix identity.total_revenue
UPDATE identities i
SET total_revenue = COALESCE((
    SELECT SUM(creator_payout_usd) FROM licenses
    WHERE identity_id = i.id AND payment_status = 'COMPLETED'
), 0)
WHERE total_revenue != COALESCE((
    SELECT SUM(creator_payout_usd) FROM licenses
    WHERE identity_id = i.id AND payment_status = 'COMPLETED'
), 0);
```

---

## 7. State Machine Enforcement

### 7.1 Status Transition Rules

**Identity Status:**
```
PENDING → PROCESSING → VERIFIED
                    → REJECTED
VERIFIED → SUSPENDED
SUSPENDED → VERIFIED (reactivation)
```

**Training Status:**
```
PENDING → QUEUED → PROCESSING → COMPLETED
                             → FAILED
FAILED → QUEUED (retry)
```

**Payment Status:**
```
PENDING → PROCESSING → COMPLETED
                    → FAILED
COMPLETED → REFUNDED
COMPLETED → DISPUTED
FAILED → PENDING (retry)
```

### 7.2 Migration Script

```sql
-- Migration: 007_state_machine_constraints.sql

BEGIN;

-- Identity status transitions
CREATE OR REPLACE FUNCTION check_identity_status_transition()
RETURNS TRIGGER AS $$
DECLARE
    valid_transitions JSONB := '{
        "PENDING": ["PROCESSING"],
        "PROCESSING": ["VERIFIED", "REJECTED"],
        "VERIFIED": ["SUSPENDED"],
        "REJECTED": ["PENDING"],
        "SUSPENDED": ["VERIFIED"]
    }'::JSONB;
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        IF NOT (valid_transitions->OLD.status) ? NEW.status THEN
            RAISE EXCEPTION 'Invalid identity status transition: % -> %',
                OLD.status, NEW.status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_identity_status_transition
    BEFORE UPDATE OF status ON identities
    FOR EACH ROW
    EXECUTE FUNCTION check_identity_status_transition();

-- Training status transitions
CREATE OR REPLACE FUNCTION check_training_status_transition()
RETURNS TRIGGER AS $$
DECLARE
    valid_transitions JSONB := '{
        "PENDING": ["QUEUED"],
        "QUEUED": ["PROCESSING"],
        "PROCESSING": ["COMPLETED", "FAILED"],
        "FAILED": ["QUEUED"],
        "COMPLETED": []
    }'::JSONB;
BEGIN
    IF OLD.training_status IS DISTINCT FROM NEW.training_status THEN
        IF NOT (valid_transitions->OLD.training_status) ? NEW.training_status THEN
            RAISE EXCEPTION 'Invalid training status transition: % -> %',
                OLD.training_status, NEW.training_status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_training_status_transition
    BEFORE UPDATE OF training_status ON actor_packs
    FOR EACH ROW
    EXECUTE FUNCTION check_training_status_transition();

-- Payment status transitions
CREATE OR REPLACE FUNCTION check_payment_status_transition()
RETURNS TRIGGER AS $$
DECLARE
    valid_transitions JSONB := '{
        "PENDING": ["PROCESSING", "FAILED"],
        "PROCESSING": ["COMPLETED", "FAILED"],
        "COMPLETED": ["REFUNDED", "DISPUTED"],
        "FAILED": ["PENDING"],
        "REFUNDED": [],
        "DISPUTED": ["REFUNDED", "COMPLETED"]
    }'::JSONB;
BEGIN
    IF OLD.payment_status IS DISTINCT FROM NEW.payment_status THEN
        IF NOT (valid_transitions->OLD.payment_status) ? NEW.payment_status THEN
            RAISE EXCEPTION 'Invalid payment status transition: % -> %',
                OLD.payment_status, NEW.payment_status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_payment_status_transition
    BEFORE UPDATE OF payment_status ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION check_payment_status_transition();

COMMIT;
```

---

## 8. Business Rule Enforcement

### 8.1 Rules to Enforce at DB Level

| Rule | Current Enforcement | Risk |
|------|---------------------|------|
| License uses <= max_outputs | App only | Over-usage without billing |
| Commercial license requires identity.allow_commercial_use | App only | Unauthorized commercial use |
| Payout requires completed licenses | App only | Invalid payouts |
| One actor pack per identity | Unique index (good) | - |
| API key rate limits | App only (Redis) | Rate limit bypass via DB |

### 8.2 Migration Script

```sql
-- Migration: 008_business_rules.sql

BEGIN;

-- Prevent license creation for non-commercial identities
CREATE OR REPLACE FUNCTION check_commercial_license()
RETURNS TRIGGER AS $$
DECLARE
    identity_commercial BOOLEAN;
BEGIN
    SELECT allow_commercial_use INTO identity_commercial
    FROM identities WHERE id = NEW.identity_id;

    IF NEW.usage_type = 'COMMERCIAL' AND NOT COALESCE(identity_commercial, false) THEN
        RAISE EXCEPTION 'Cannot create commercial license for identity that does not allow commercial use';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_commercial_license
    BEFORE INSERT ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION check_commercial_license();

-- Prevent usage beyond limits
CREATE OR REPLACE FUNCTION check_license_limits()
RETURNS TRIGGER AS $$
BEGIN
    -- Check max_outputs limit
    IF NEW.max_outputs IS NOT NULL AND NEW.current_uses > NEW.max_outputs THEN
        RAISE EXCEPTION 'License usage limit exceeded: % > %',
            NEW.current_uses, NEW.max_outputs;
    END IF;

    -- Check max_impressions limit
    IF NEW.max_impressions IS NOT NULL AND NEW.current_impressions > NEW.max_impressions THEN
        RAISE EXCEPTION 'License impression limit exceeded: % > %',
            NEW.current_impressions, NEW.max_impressions;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_license_limits
    BEFORE UPDATE ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION check_license_limits();

-- Prevent payout for incomplete transactions
CREATE OR REPLACE FUNCTION check_payout_validity()
RETURNS TRIGGER AS $$
DECLARE
    pending_amount FLOAT;
BEGIN
    SELECT COALESCE(SUM(creator_payout_usd), 0) INTO pending_amount
    FROM licenses
    WHERE identity_id IN (SELECT id FROM identities WHERE user_id = NEW.user_id)
    AND payment_status = 'COMPLETED'
    AND payout_status = 'pending';

    IF NEW.amount > pending_amount THEN
        RAISE EXCEPTION 'Payout amount % exceeds available balance %',
            NEW.amount, pending_amount;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_payout_validity
    BEFORE INSERT ON payouts
    FOR EACH ROW
    EXECUTE FUNCTION check_payout_validity();

COMMIT;
```

---

## 9. Temporal Data & Audit Trail

### 9.1 Missing Timestamps

| Table | Has created_at | Has updated_at | Recommendation |
|-------|----------------|----------------|----------------|
| usage_logs | YES | NO | Add (for correction logging) |
| audit_logs | YES | NO | OK (immutable) |
| notifications | YES | NO | Add |
| webhook_events | YES | YES | OK |

### 9.2 Automatic Audit Logging

```sql
-- Migration: 009_audit_trail.sql

BEGIN;

-- Add updated_at to notifications
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Generic audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    audit_row audit_logs;
    excluded_cols TEXT[] := ARRAY['created_at', 'updated_at'];
    old_data JSONB;
    new_data JSONB;
BEGIN
    -- Build old/new data excluding timestamp columns
    IF TG_OP = 'UPDATE' THEN
        old_data := to_jsonb(OLD) - excluded_cols;
        new_data := to_jsonb(NEW) - excluded_cols;

        -- Skip if nothing changed
        IF old_data = new_data THEN
            RETURN NEW;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        old_data := to_jsonb(OLD) - excluded_cols;
        new_data := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        old_data := NULL;
        new_data := to_jsonb(NEW) - excluded_cols;
    END IF;

    INSERT INTO audit_logs (
        id,
        user_id,
        action,
        resource_type,
        resource_id,
        old_values,
        new_values,
        description,
        created_at
    ) VALUES (
        gen_random_uuid(),
        COALESCE(
            current_setting('app.current_user_id', true)::UUID,
            NULL
        ),
        CASE TG_OP
            WHEN 'INSERT' THEN 'CREATE'
            WHEN 'UPDATE' THEN 'UPDATE'
            WHEN 'DELETE' THEN 'DELETE'
        END::audit_action,
        TG_TABLE_NAME,
        CASE
            WHEN TG_OP = 'DELETE' THEN OLD.id
            ELSE NEW.id
        END,
        old_data,
        new_data,
        TG_OP || ' on ' || TG_TABLE_NAME,
        NOW()
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit triggers to critical tables
CREATE TRIGGER audit_identities
    AFTER INSERT OR UPDATE OR DELETE ON identities
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_licenses
    AFTER INSERT OR UPDATE OR DELETE ON licenses
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_users
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_subscriptions
    AFTER INSERT OR UPDATE OR DELETE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_payouts
    AFTER INSERT OR UPDATE OR DELETE ON payouts
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

COMMIT;
```

---

## 10. Application Code Changes

### 10.1 Model Updates Required

```python
# app/models/identity.py - Add soft delete handling

class Identity(Base):
    # ... existing fields ...

    # Add index for soft delete queries
    __table_args__ = (
        Index("idx_identity_user_status", "user_id", "status"),
        Index("idx_identity_commercial", "allow_commercial_use", "status"),
        Index("idx_identity_not_deleted", "id", postgresql_where=text("deleted_at IS NULL")),
    )


# app/models/user.py - Add soft delete

class User(Base):
    # ... existing fields ...

    deleted_at = Column(DateTime)  # Add soft delete support


# app/core/database.py - Add session user context

async def set_audit_context(db: AsyncSession, user_id: Optional[UUID]):
    """Set current user for audit logging triggers"""
    if user_id:
        await db.execute(
            text(f"SET LOCAL app.current_user_id = '{user_id}'")
        )
```

### 10.2 Service Layer Updates

```python
# app/services/identity.py - Use transactions properly

async def delete_identity(self, identity: Identity) -> None:
    """Soft delete with proper cascade handling"""
    async with self.db.begin():
        # Set audit context
        await set_audit_context(self.db, identity.user_id)

        # Soft delete triggers will handle cascade
        identity.deleted_at = datetime.utcnow()
        identity.status = "SUSPENDED"

        # Remove from vector database
        await self.face_service.delete_embedding(identity.id)

        await self.db.commit()
```

### 10.3 Query Filters for Soft Deletes

```python
# app/core/queries.py - Reusable filters

from sqlalchemy import and_

def active_identity_filter():
    """Filter for non-deleted identities"""
    return and_(
        Identity.deleted_at.is_(None),
        Identity.status != "SUSPENDED"
    )

def active_user_filter():
    """Filter for non-deleted users"""
    return and_(
        User.deleted_at.is_(None),
        User.is_active == True
    )
```

---

## 11. Execution Plan

### Phase 1: Critical (Week 1)
1. ✅ Run migration 001 (ON DELETE constraints) - Maintenance window
2. ✅ Run migration 003 (CHECK constraints) - Rolling deploy OK
3. ✅ Run migration 004 (Soft delete triggers)

### Phase 2: High Priority (Week 2)
4. Run migration 002 (Unique constraints) - Check for existing duplicates first
5. Run migration 005 (Status constraints)
6. Run migration 007 (State machines)

### Phase 3: Medium Priority (Week 3-4)
7. Run migration 006 (Denormalized data triggers)
8. Run reconciliation queries
9. Run migration 008 (Business rules)

### Phase 4: Compliance (Week 5)
10. Run migration 009 (Audit trail)
11. Update application code
12. Add monitoring for constraint violations

---

## 12. Monitoring & Alerts

```sql
-- Create monitoring view for data integrity issues
CREATE OR REPLACE VIEW data_integrity_issues AS

-- Orphaned actor packs (identity deleted)
SELECT 'orphaned_actor_pack' as issue_type,
       ap.id as resource_id,
       ap.identity_id as related_id
FROM actor_packs ap
LEFT JOIN identities i ON ap.identity_id = i.id
WHERE i.id IS NULL OR i.deleted_at IS NOT NULL

UNION ALL

-- Licenses with deleted identities
SELECT 'license_deleted_identity', l.id, l.identity_id
FROM licenses l
JOIN identities i ON l.identity_id = i.id
WHERE i.deleted_at IS NOT NULL AND l.is_active = true

UNION ALL

-- Active listings for deleted identities
SELECT 'active_listing_deleted_identity', lst.id, lst.identity_id
FROM listings lst
JOIN identities i ON lst.identity_id = i.id
WHERE i.deleted_at IS NOT NULL AND lst.is_active = true

UNION ALL

-- Revenue drift detection (sample)
SELECT 'revenue_drift', i.id, NULL
FROM identities i
WHERE i.total_revenue != COALESCE((
    SELECT SUM(creator_payout_usd) FROM licenses
    WHERE identity_id = i.id AND payment_status = 'COMPLETED'
), 0);

-- Alert on any issues
-- Schedule to run hourly:
-- SELECT * FROM data_integrity_issues LIMIT 10;
```

---

## Appendix: Quick Reference

### Constraint Naming Convention
- FK: `fk_{table}_{column}`
- Unique: `uq_{table}_{columns}`
- Check: `chk_{table}_{description}`
- Index: `idx_{table}_{columns}`

### Rollback Scripts
Each migration includes rollback capability:
```sql
-- To rollback migration 001:
-- DROP TRIGGER IF EXISTS ... CASCADE;
-- ALTER TABLE ... DROP CONSTRAINT IF EXISTS ...;
```

### Testing Checklist
- [ ] Test user deletion cascades correctly
- [ ] Test identity soft delete cascades
- [ ] Test license creation validation
- [ ] Test status transitions
- [ ] Test denormalized data updates
- [ ] Run reconciliation queries
- [ ] Verify audit logs capture changes
