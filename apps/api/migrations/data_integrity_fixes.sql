-- =============================================================================
-- DATA INTEGRITY MIGRATION SCRIPT
-- ActorHub.ai Platform
-- Generated: 2024-12-21
-- =============================================================================
-- EXECUTION ORDER:
--   1. Run pre-check queries to identify existing violations
--   2. Fix any data issues found
--   3. Run migrations in order (001-009)
--   4. Verify with post-check queries
-- =============================================================================

-- #############################################################################
-- PRE-MIGRATION CHECKS
-- Run these BEFORE applying migrations to identify existing data issues
-- #############################################################################

-- Check for duplicate identity names per user
SELECT user_id, lower(display_name) as name, COUNT(*) as cnt
FROM identities
WHERE deleted_at IS NULL
GROUP BY user_id, lower(display_name)
HAVING COUNT(*) > 1;

-- Check for multiple active subscriptions per user
SELECT user_id, COUNT(*) as active_count
FROM subscriptions
WHERE status = 'ACTIVE'
GROUP BY user_id
HAVING COUNT(*) > 1;

-- Check for negative prices
SELECT id, price_usd FROM licenses WHERE price_usd < 0;
SELECT id, base_license_fee FROM identities WHERE base_license_fee < 0;

-- Check for invalid status values
SELECT DISTINCT status FROM identities
WHERE status NOT IN ('PENDING', 'PROCESSING', 'VERIFIED', 'REJECTED', 'SUSPENDED');

SELECT DISTINCT training_status FROM actor_packs
WHERE training_status NOT IN ('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED');

-- Check for orphaned records
SELECT ap.id, ap.identity_id FROM actor_packs ap
LEFT JOIN identities i ON ap.identity_id = i.id
WHERE i.id IS NULL;

-- Check revenue drift
SELECT i.id, i.display_name, i.total_revenue,
       COALESCE(SUM(l.creator_payout_usd), 0) as actual_revenue
FROM identities i
LEFT JOIN licenses l ON l.identity_id = i.id AND l.payment_status = 'COMPLETED'
GROUP BY i.id
HAVING i.total_revenue != COALESCE(SUM(l.creator_payout_usd), 0);


-- #############################################################################
-- MIGRATION 001: ON DELETE CONSTRAINTS
-- CRITICAL: Run during maintenance window - may lock tables briefly
-- #############################################################################

BEGIN;

-- Add soft delete to users table first
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- identities.user_id -> CASCADE
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
ALTER TABLE licenses ALTER COLUMN identity_id DROP NOT NULL;
ALTER TABLE licenses DROP CONSTRAINT IF EXISTS licenses_identity_id_fkey;
ALTER TABLE licenses ADD CONSTRAINT licenses_identity_id_fkey
    FOREIGN KEY (identity_id) REFERENCES identities(id) ON DELETE SET NULL;

-- licenses.licensee_id -> SET NULL
ALTER TABLE licenses ALTER COLUMN licensee_id DROP NOT NULL;
ALTER TABLE licenses DROP CONSTRAINT IF EXISTS licenses_licensee_id_fkey;
ALTER TABLE licenses ADD CONSTRAINT licenses_licensee_id_fkey
    FOREIGN KEY (licensee_id) REFERENCES users(id) ON DELETE SET NULL;

-- transactions.license_id -> SET NULL
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_license_id_fkey;
ALTER TABLE transactions ADD CONSTRAINT transactions_license_id_fkey
    FOREIGN KEY (license_id) REFERENCES licenses(id) ON DELETE SET NULL;

-- transactions.user_id -> SET NULL
ALTER TABLE transactions ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_user_id_fkey;
ALTER TABLE transactions ADD CONSTRAINT transactions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- notifications.user_id -> CASCADE
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_user_id_fkey;
ALTER TABLE notifications ADD CONSTRAINT notifications_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- subscriptions.user_id -> CASCADE
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_user_id_fkey;
ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- payouts.user_id -> SET NULL (preserve financial records)
ALTER TABLE payouts ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE payouts DROP CONSTRAINT IF EXISTS payouts_user_id_fkey;
ALTER TABLE payouts ADD CONSTRAINT payouts_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

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


-- #############################################################################
-- MIGRATION 002: UNIQUE CONSTRAINTS
-- Safe to run anytime - will fail if duplicates exist
-- #############################################################################

BEGIN;

-- Prevent duplicate identity names per user (partial index for soft deletes)
CREATE UNIQUE INDEX IF NOT EXISTS idx_identity_user_display_name
    ON identities(user_id, lower(display_name))
    WHERE deleted_at IS NULL;

-- One active listing per identity
CREATE UNIQUE INDEX IF NOT EXISTS idx_listing_identity_unique
    ON listings(identity_id)
    WHERE is_active = true;

-- One active subscription per user
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


-- #############################################################################
-- MIGRATION 003: CHECK CONSTRAINTS
-- Safe to run anytime - validates existing data
-- #############################################################################

BEGIN;

-- License constraints
ALTER TABLE licenses ADD CONSTRAINT IF NOT EXISTS chk_license_price_positive
    CHECK (price_usd >= 0);

ALTER TABLE licenses ADD CONSTRAINT IF NOT EXISTS chk_license_payout_valid
    CHECK (creator_payout_usd IS NULL OR (creator_payout_usd >= 0 AND creator_payout_usd <= price_usd));

ALTER TABLE licenses ADD CONSTRAINT IF NOT EXISTS chk_license_fee_percent
    CHECK (platform_fee_percent >= 0 AND platform_fee_percent <= 100);

ALTER TABLE licenses ADD CONSTRAINT IF NOT EXISTS chk_license_uses_positive
    CHECK (current_uses >= 0 AND current_impressions >= 0);

ALTER TABLE licenses ADD CONSTRAINT IF NOT EXISTS chk_license_dates_valid
    CHECK (valid_until IS NULL OR valid_until >= valid_from);

-- Identity constraints
ALTER TABLE identities ADD CONSTRAINT IF NOT EXISTS chk_identity_revenue_share
    CHECK (revenue_share_percent >= 0 AND revenue_share_percent <= 100);

ALTER TABLE identities ADD CONSTRAINT IF NOT EXISTS chk_identity_prices_positive
    CHECK (base_license_fee >= 0 AND hourly_rate >= 0 AND per_image_rate >= 0);

ALTER TABLE identities ADD CONSTRAINT IF NOT EXISTS chk_identity_stats_positive
    CHECK (total_verifications >= 0 AND total_licenses >= 0 AND total_revenue >= 0);

-- Actor pack constraints
ALTER TABLE actor_packs ADD CONSTRAINT IF NOT EXISTS chk_pack_progress_range
    CHECK (training_progress >= 0 AND training_progress <= 100);

ALTER TABLE actor_packs ADD CONSTRAINT IF NOT EXISTS chk_pack_quality_range
    CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100));

ALTER TABLE actor_packs ADD CONSTRAINT IF NOT EXISTS chk_pack_prices_positive
    CHECK (base_price_usd >= 0 AND price_per_second_usd >= 0 AND price_per_image_usd >= 0);

ALTER TABLE actor_packs ADD CONSTRAINT IF NOT EXISTS chk_pack_stats_positive
    CHECK (total_downloads >= 0 AND total_uses >= 0 AND total_revenue_usd >= 0);

-- Payout constraints
ALTER TABLE payouts ADD CONSTRAINT IF NOT EXISTS chk_payout_amount_positive
    CHECK (amount > 0);

ALTER TABLE payouts ADD CONSTRAINT IF NOT EXISTS chk_payout_net_valid
    CHECK (net_amount IS NULL OR (net_amount >= 0 AND net_amount <= amount));

ALTER TABLE payouts ADD CONSTRAINT IF NOT EXISTS chk_payout_fee_positive
    CHECK (fee >= 0);

-- Subscription constraints
ALTER TABLE subscriptions ADD CONSTRAINT IF NOT EXISTS chk_subscription_amount_positive
    CHECK (amount >= 0);

ALTER TABLE subscriptions ADD CONSTRAINT IF NOT EXISTS chk_subscription_limits_positive
    CHECK (identities_limit >= 0 AND api_calls_limit >= 0 AND storage_limit_mb >= 0);

-- Usage log constraints
ALTER TABLE usage_logs ADD CONSTRAINT IF NOT EXISTS chk_usage_response_time
    CHECK (response_time_ms IS NULL OR response_time_ms >= 0);

ALTER TABLE usage_logs ADD CONSTRAINT IF NOT EXISTS chk_usage_similarity
    CHECK (similarity_score IS NULL OR (similarity_score >= 0 AND similarity_score <= 1));

COMMIT;


-- #############################################################################
-- MIGRATION 004: STATUS VALUE CONSTRAINTS
-- Ensures only valid enum values are stored
-- #############################################################################

BEGIN;

ALTER TABLE identities ADD CONSTRAINT IF NOT EXISTS chk_identity_status
    CHECK (status IN ('PENDING', 'PROCESSING', 'VERIFIED', 'REJECTED', 'SUSPENDED'));

ALTER TABLE actor_packs ADD CONSTRAINT IF NOT EXISTS chk_training_status
    CHECK (training_status IN ('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'));

ALTER TABLE licenses ADD CONSTRAINT IF NOT EXISTS chk_payment_status
    CHECK (payment_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED'));

ALTER TABLE licenses ADD CONSTRAINT IF NOT EXISTS chk_license_type
    CHECK (license_type IN ('SINGLE_USE', 'SUBSCRIPTION', 'UNLIMITED', 'CUSTOM'));

ALTER TABLE licenses ADD CONSTRAINT IF NOT EXISTS chk_usage_type
    CHECK (usage_type IN ('PERSONAL', 'COMMERCIAL', 'EDITORIAL', 'EDUCATIONAL'));

ALTER TABLE transactions ADD CONSTRAINT IF NOT EXISTS chk_transaction_type
    CHECK (type IN ('PURCHASE', 'PAYOUT', 'REFUND', 'FEE', 'SUBSCRIPTION', 'CREDIT'));

ALTER TABLE transactions ADD CONSTRAINT IF NOT EXISTS chk_transaction_status
    CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED'));

COMMIT;


-- #############################################################################
-- MIGRATION 005: SOFT DELETE CASCADE TRIGGERS
-- Automatically handles cascade on soft delete
-- #############################################################################

BEGIN;

-- Function to cascade identity soft deletes
CREATE OR REPLACE FUNCTION cascade_identity_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
        -- Deactivate listings
        UPDATE listings
        SET is_active = false, updated_at = NOW()
        WHERE identity_id = NEW.id AND is_active = true;

        -- Cancel pending training
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

        -- Deactivate active licenses
        UPDATE licenses
        SET is_active = false, updated_at = NOW()
        WHERE identity_id = NEW.id AND is_active = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_identity_soft_delete ON identities;
CREATE TRIGGER trg_identity_soft_delete
    AFTER UPDATE OF deleted_at ON identities
    FOR EACH ROW
    EXECUTE FUNCTION cascade_identity_soft_delete();

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
        WHERE user_id = NEW.id AND is_active = true;

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

DROP TRIGGER IF EXISTS trg_user_soft_delete ON users;
CREATE TRIGGER trg_user_soft_delete
    AFTER UPDATE OF deleted_at ON users
    FOR EACH ROW
    EXECUTE FUNCTION cascade_user_soft_delete();

COMMIT;


-- #############################################################################
-- MIGRATION 006: DENORMALIZED DATA UPDATE TRIGGERS
-- Keeps aggregate fields in sync
-- #############################################################################

BEGIN;

-- Update identity verification count on usage log insert
CREATE OR REPLACE FUNCTION update_identity_verification_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.action = 'verify' AND NEW.matched = true AND NEW.identity_id IS NOT NULL THEN
        UPDATE identities
        SET total_verifications = total_verifications + 1,
            updated_at = NOW()
        WHERE id = NEW.identity_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_usage_log_verification ON usage_logs;
CREATE TRIGGER trg_usage_log_verification
    AFTER INSERT ON usage_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_identity_verification_count();

-- Update identity license count
CREATE OR REPLACE FUNCTION update_identity_license_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.identity_id IS NOT NULL THEN
        UPDATE identities
        SET total_licenses = total_licenses + 1,
            updated_at = NOW()
        WHERE id = NEW.identity_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_license_count ON licenses;
CREATE TRIGGER trg_license_count
    AFTER INSERT ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION update_identity_license_count();

-- Update revenue on license payment completion
CREATE OR REPLACE FUNCTION update_identity_revenue()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.payment_status = 'COMPLETED' AND
       (OLD.payment_status IS NULL OR OLD.payment_status != 'COMPLETED') AND
       NEW.identity_id IS NOT NULL THEN
        UPDATE identities
        SET total_revenue = total_revenue + COALESCE(NEW.creator_payout_usd, 0),
            updated_at = NOW()
        WHERE id = NEW.identity_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_license_revenue ON licenses;
CREATE TRIGGER trg_license_revenue
    AFTER UPDATE OF payment_status ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION update_identity_revenue();

-- Update actor pack download count
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

DROP TRIGGER IF EXISTS trg_usage_log_download ON usage_logs;
CREATE TRIGGER trg_usage_log_download
    AFTER INSERT ON usage_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_actor_pack_downloads();

-- Update listing license count
CREATE OR REPLACE FUNCTION update_listing_license_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.identity_id IS NOT NULL THEN
        UPDATE listings
        SET license_count = license_count + 1,
            updated_at = NOW()
        WHERE identity_id = NEW.identity_id AND is_active = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_listing_license_count ON licenses;
CREATE TRIGGER trg_listing_license_count
    AFTER INSERT ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION update_listing_license_count();

COMMIT;


-- #############################################################################
-- MIGRATION 007: BUSINESS RULE ENFORCEMENT
-- Database-level enforcement of critical business rules
-- #############################################################################

BEGIN;

-- Prevent commercial license for non-commercial identity
CREATE OR REPLACE FUNCTION check_commercial_license()
RETURNS TRIGGER AS $$
DECLARE
    identity_commercial BOOLEAN;
BEGIN
    IF NEW.identity_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT allow_commercial_use INTO identity_commercial
    FROM identities WHERE id = NEW.identity_id;

    IF NEW.usage_type = 'COMMERCIAL' AND NOT COALESCE(identity_commercial, false) THEN
        RAISE EXCEPTION 'Cannot create commercial license for identity that does not allow commercial use';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_commercial_license ON licenses;
CREATE TRIGGER trg_check_commercial_license
    BEFORE INSERT ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION check_commercial_license();

-- Prevent usage beyond limits
CREATE OR REPLACE FUNCTION check_license_limits()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.max_outputs IS NOT NULL AND NEW.current_uses > NEW.max_outputs THEN
        RAISE EXCEPTION 'License usage limit exceeded: % > %',
            NEW.current_uses, NEW.max_outputs;
    END IF;

    IF NEW.max_impressions IS NOT NULL AND NEW.current_impressions > NEW.max_impressions THEN
        RAISE EXCEPTION 'License impression limit exceeded: % > %',
            NEW.current_impressions, NEW.max_impressions;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_license_limits ON licenses;
CREATE TRIGGER trg_check_license_limits
    BEFORE UPDATE ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION check_license_limits();

COMMIT;


-- #############################################################################
-- MIGRATION 008: STATE MACHINE ENFORCEMENT
-- Ensures valid status transitions
-- #############################################################################

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
    allowed_next JSONB;
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        allowed_next := valid_transitions->OLD.status;
        IF allowed_next IS NULL OR NOT allowed_next ? NEW.status THEN
            RAISE EXCEPTION 'Invalid identity status transition: % -> %', OLD.status, NEW.status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_identity_status_transition ON identities;
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
    allowed_next JSONB;
BEGIN
    IF OLD.training_status IS DISTINCT FROM NEW.training_status THEN
        allowed_next := valid_transitions->OLD.training_status;
        IF allowed_next IS NULL OR NOT allowed_next ? NEW.training_status THEN
            RAISE EXCEPTION 'Invalid training status transition: % -> %',
                OLD.training_status, NEW.training_status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_training_status_transition ON actor_packs;
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
    allowed_next JSONB;
BEGIN
    IF OLD.payment_status IS DISTINCT FROM NEW.payment_status THEN
        allowed_next := valid_transitions->OLD.payment_status;
        IF allowed_next IS NULL OR NOT allowed_next ? NEW.payment_status THEN
            RAISE EXCEPTION 'Invalid payment status transition: % -> %',
                OLD.payment_status, NEW.payment_status;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_payment_status_transition ON licenses;
CREATE TRIGGER trg_payment_status_transition
    BEFORE UPDATE OF payment_status ON licenses
    FOR EACH ROW
    EXECUTE FUNCTION check_payment_status_transition();

COMMIT;


-- #############################################################################
-- MIGRATION 009: AUTOMATIC AUDIT LOGGING
-- Creates comprehensive audit trail for compliance
-- #############################################################################

BEGIN;

-- Add updated_at to tables missing it
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Generic audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    excluded_cols TEXT[] := ARRAY['created_at', 'updated_at'];
    old_data JSONB;
    new_data JSONB;
    current_user_id UUID;
BEGIN
    -- Try to get current user from session variable
    BEGIN
        current_user_id := current_setting('app.current_user_id', true)::UUID;
    EXCEPTION WHEN OTHERS THEN
        current_user_id := NULL;
    END;

    -- Build old/new data excluding timestamp columns
    IF TG_OP = 'UPDATE' THEN
        old_data := to_jsonb(OLD) - excluded_cols;
        new_data := to_jsonb(NEW) - excluded_cols;

        -- Skip if nothing meaningful changed
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
        current_user_id,
        CASE TG_OP
            WHEN 'INSERT' THEN 'CREATE'::audit_action
            WHEN 'UPDATE' THEN 'UPDATE'::audit_action
            WHEN 'DELETE' THEN 'DELETE'::audit_action
        END,
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
DROP TRIGGER IF EXISTS audit_identities ON identities;
CREATE TRIGGER audit_identities
    AFTER INSERT OR UPDATE OR DELETE ON identities
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

DROP TRIGGER IF EXISTS audit_licenses ON licenses;
CREATE TRIGGER audit_licenses
    AFTER INSERT OR UPDATE OR DELETE ON licenses
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

DROP TRIGGER IF EXISTS audit_users ON users;
CREATE TRIGGER audit_users
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

DROP TRIGGER IF EXISTS audit_subscriptions ON subscriptions;
CREATE TRIGGER audit_subscriptions
    AFTER INSERT OR UPDATE OR DELETE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

DROP TRIGGER IF EXISTS audit_payouts ON payouts;
CREATE TRIGGER audit_payouts
    AFTER INSERT OR UPDATE OR DELETE ON payouts
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

COMMIT;


-- #############################################################################
-- DATA RECONCILIATION QUERIES
-- Run after all migrations to fix any drifted data
-- #############################################################################

-- Fix identity.total_verifications
UPDATE identities i
SET total_verifications = sub.actual_count
FROM (
    SELECT identity_id, COUNT(*) as actual_count
    FROM usage_logs
    WHERE action = 'verify' AND matched = true
    GROUP BY identity_id
) sub
WHERE i.id = sub.identity_id
AND i.total_verifications != sub.actual_count;

-- Fix identity.total_licenses
UPDATE identities i
SET total_licenses = sub.actual_count
FROM (
    SELECT identity_id, COUNT(*) as actual_count
    FROM licenses
    GROUP BY identity_id
) sub
WHERE i.id = sub.identity_id
AND i.total_licenses != sub.actual_count;

-- Fix identity.total_revenue
UPDATE identities i
SET total_revenue = COALESCE(sub.actual_revenue, 0)
FROM (
    SELECT identity_id, SUM(creator_payout_usd) as actual_revenue
    FROM licenses
    WHERE payment_status = 'COMPLETED'
    GROUP BY identity_id
) sub
WHERE i.id = sub.identity_id
AND i.total_revenue != COALESCE(sub.actual_revenue, 0);

-- Fix actor_pack.total_downloads
UPDATE actor_packs ap
SET total_downloads = sub.actual_count
FROM (
    SELECT actor_pack_id, COUNT(*) as actual_count
    FROM usage_logs
    WHERE action = 'download'
    GROUP BY actor_pack_id
) sub
WHERE ap.id = sub.actor_pack_id
AND ap.total_downloads != sub.actual_count;


-- #############################################################################
-- POST-MIGRATION VERIFICATION
-- Run these after all migrations to verify integrity
-- #############################################################################

-- Verify no orphaned records exist
SELECT 'orphaned_actor_packs' as check_name,
       COUNT(*) as count
FROM actor_packs ap
LEFT JOIN identities i ON ap.identity_id = i.id
WHERE i.id IS NULL

UNION ALL

SELECT 'orphaned_listings',
       COUNT(*)
FROM listings l
LEFT JOIN identities i ON l.identity_id = i.id
WHERE i.id IS NULL

UNION ALL

SELECT 'active_listings_deleted_identity',
       COUNT(*)
FROM listings l
JOIN identities i ON l.identity_id = i.id
WHERE i.deleted_at IS NOT NULL AND l.is_active = true

UNION ALL

SELECT 'invalid_identity_status',
       COUNT(*)
FROM identities
WHERE status NOT IN ('PENDING', 'PROCESSING', 'VERIFIED', 'REJECTED', 'SUSPENDED')

UNION ALL

SELECT 'negative_prices',
       COUNT(*)
FROM licenses
WHERE price_usd < 0 OR creator_payout_usd < 0;

-- If all counts are 0, migrations were successful!
