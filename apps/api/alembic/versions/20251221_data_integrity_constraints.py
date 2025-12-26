"""Add data integrity constraints and indexes

Revision ID: 20251221_data_integrity
Revises: 20251218_stripe_connect
Create Date: 2025-12-21

Comprehensive data integrity migration adding:
- Foreign key ON DELETE behaviors (CASCADE/SET NULL)
- CHECK constraints for data validation
- Partial unique indexes for soft-delete aware uniqueness
- Additional indexes for common query patterns
- Soft delete support for users table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251221_data_integrity'
down_revision = '20251218_stripe_connect'
branch_labels = None
depends_on = None


def upgrade():
    """Add all data integrity constraints"""

    # ============================================================
    # SECTION 1: Users table - Add soft delete and constraints
    # ============================================================

    # Add deleted_at column for soft delete
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    # Add CHECK constraints for users
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT chk_user_role
        CHECK (role IN ('USER', 'CREATOR', 'ADMIN'))
    """)

    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT chk_user_tier
        CHECK (tier IN ('FREE', 'PRO', 'ENTERPRISE'))
    """)

    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT chk_user_email_format
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')
    """)

    # Add partial indexes for soft-deleted records
    op.create_index(
        'idx_user_not_deleted',
        'users',
        ['id'],
        postgresql_where='deleted_at IS NULL'
    )

    op.create_index(
        'idx_user_email_active',
        'users',
        ['email'],
        postgresql_where='deleted_at IS NULL AND is_active = true'
    )

    # ============================================================
    # SECTION 2: API Keys - Add FK CASCADE and constraints
    # ============================================================

    # Drop and recreate FK with ON DELETE CASCADE
    op.drop_constraint('api_keys_user_id_fkey', 'api_keys', type_='foreignkey')
    op.create_foreign_key(
        'api_keys_user_id_fkey',
        'api_keys', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE api_keys
        ADD CONSTRAINT chk_apikey_rate_limit_positive
        CHECK (rate_limit > 0)
    """)

    op.execute("""
        ALTER TABLE api_keys
        ADD CONSTRAINT chk_apikey_usage_count_positive
        CHECK (usage_count >= 0)
    """)

    # Unique active key name per user
    op.create_index(
        'idx_apikey_user_name_unique',
        'api_keys',
        ['user_id', 'name'],
        unique=True,
        postgresql_where='is_active = true'
    )

    # ============================================================
    # SECTION 3: Identities - Add FK CASCADE and constraints
    # ============================================================

    # Drop and recreate FK with ON DELETE CASCADE
    op.drop_constraint('identities_user_id_fkey', 'identities', type_='foreignkey')
    op.create_foreign_key(
        'identities_user_id_fkey',
        'identities', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE identities
        ADD CONSTRAINT chk_identity_status
        CHECK (status IN ('PENDING', 'PROCESSING', 'VERIFIED', 'REJECTED', 'SUSPENDED'))
    """)

    op.execute("""
        ALTER TABLE identities
        ADD CONSTRAINT chk_identity_protection_level
        CHECK (protection_level IN ('FREE', 'PRO', 'ENTERPRISE'))
    """)

    op.execute("""
        ALTER TABLE identities
        ADD CONSTRAINT chk_identity_base_fee_positive
        CHECK (base_license_fee >= 0)
    """)

    op.execute("""
        ALTER TABLE identities
        ADD CONSTRAINT chk_identity_hourly_rate_positive
        CHECK (hourly_rate >= 0)
    """)

    op.execute("""
        ALTER TABLE identities
        ADD CONSTRAINT chk_identity_per_image_rate_positive
        CHECK (per_image_rate >= 0)
    """)

    op.execute("""
        ALTER TABLE identities
        ADD CONSTRAINT chk_identity_revenue_share_range
        CHECK (revenue_share_percent >= 0 AND revenue_share_percent <= 100)
    """)

    op.execute("""
        ALTER TABLE identities
        ADD CONSTRAINT chk_identity_total_verifications_positive
        CHECK (total_verifications >= 0)
    """)

    op.execute("""
        ALTER TABLE identities
        ADD CONSTRAINT chk_identity_total_licenses_positive
        CHECK (total_licenses >= 0)
    """)

    op.execute("""
        ALTER TABLE identities
        ADD CONSTRAINT chk_identity_total_revenue_positive
        CHECK (total_revenue >= 0)
    """)

    # Unique display_name per user (for non-deleted)
    op.create_index(
        'idx_identity_user_display_name_unique',
        'identities',
        ['user_id', 'display_name'],
        unique=True,
        postgresql_where='deleted_at IS NULL'
    )

    # Additional useful indexes
    op.create_index('idx_identity_user_status', 'identities', ['user_id', 'status'])
    op.create_index('idx_identity_commercial', 'identities', ['allow_commercial_use', 'status'])
    op.create_index(
        'idx_identity_not_deleted',
        'identities',
        ['id'],
        postgresql_where='deleted_at IS NULL'
    )

    # ============================================================
    # SECTION 4: Actor Packs - Add FK CASCADE and constraints
    # ============================================================

    # Drop and recreate FK with ON DELETE CASCADE
    op.drop_constraint('actor_packs_identity_id_fkey', 'actor_packs', type_='foreignkey')
    op.create_foreign_key(
        'actor_packs_identity_id_fkey',
        'actor_packs', 'identities',
        ['identity_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_training_status
        CHECK (training_status IN ('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED'))
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_progress_range
        CHECK (training_progress >= 0 AND training_progress <= 100)
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_quality_range
        CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 100))
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_authenticity_range
        CHECK (authenticity_score IS NULL OR (authenticity_score >= 0 AND authenticity_score <= 100))
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_consistency_range
        CHECK (consistency_score IS NULL OR (consistency_score >= 0 AND consistency_score <= 100))
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_voice_quality_range
        CHECK (voice_quality_score IS NULL OR (voice_quality_score >= 0 AND voice_quality_score <= 100))
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_base_price_positive
        CHECK (base_price_usd >= 0)
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_price_per_second_positive
        CHECK (price_per_second_usd >= 0)
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_price_per_image_positive
        CHECK (price_per_image_usd >= 0)
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_downloads_positive
        CHECK (total_downloads >= 0)
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_uses_positive
        CHECK (total_uses >= 0)
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_revenue_positive
        CHECK (total_revenue_usd >= 0)
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_rating_count_positive
        CHECK (rating_count >= 0)
    """)

    op.execute("""
        ALTER TABLE actor_packs
        ADD CONSTRAINT chk_actor_pack_file_size_positive
        CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0)
    """)

    # ============================================================
    # SECTION 5: Licenses - Add FK SET NULL and constraints
    # ============================================================

    # Drop and recreate FKs with ON DELETE SET NULL (preserve financial records)
    op.drop_constraint('licenses_identity_id_fkey', 'licenses', type_='foreignkey')
    op.create_foreign_key(
        'licenses_identity_id_fkey',
        'licenses', 'identities',
        ['identity_id'], ['id'],
        ondelete='SET NULL'
    )

    op.drop_constraint('licenses_licensee_id_fkey', 'licenses', type_='foreignkey')
    op.create_foreign_key(
        'licenses_licensee_id_fkey',
        'licenses', 'users',
        ['licensee_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_type
        CHECK (license_type IN ('SINGLE_USE', 'SUBSCRIPTION', 'UNLIMITED', 'CUSTOM'))
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_usage_type
        CHECK (usage_type IN ('PERSONAL', 'COMMERCIAL', 'EDITORIAL', 'EDUCATIONAL'))
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_payment_status
        CHECK (payment_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED'))
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_price_positive
        CHECK (price_usd >= 0)
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_payout_valid
        CHECK (creator_payout_usd IS NULL OR (creator_payout_usd >= 0 AND creator_payout_usd <= price_usd))
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_fee_percent_range
        CHECK (platform_fee_percent >= 0 AND platform_fee_percent <= 100)
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_uses_positive
        CHECK (current_uses >= 0)
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_impressions_positive
        CHECK (current_impressions >= 0)
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_duration_positive
        CHECK (current_duration_seconds >= 0)
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_dates_valid
        CHECK (valid_until IS NULL OR valid_until >= valid_from)
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_max_impressions
        CHECK (max_impressions IS NULL OR max_impressions > 0)
    """)

    op.execute("""
        ALTER TABLE licenses
        ADD CONSTRAINT chk_license_max_outputs
        CHECK (max_outputs IS NULL OR max_outputs > 0)
    """)

    # Add indexes
    op.create_index('idx_license_dates', 'licenses', ['valid_from', 'valid_until'])
    op.create_index('idx_license_active', 'licenses', ['is_active', 'valid_until'])

    # ============================================================
    # SECTION 6: Transactions - Add FK SET NULL and constraints
    # ============================================================

    # Drop and recreate FKs with ON DELETE SET NULL
    op.drop_constraint('transactions_license_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'transactions_license_id_fkey',
        'transactions', 'licenses',
        ['license_id'], ['id'],
        ondelete='SET NULL'
    )

    op.drop_constraint('transactions_user_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key(
        'transactions_user_id_fkey',
        'transactions', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE transactions
        ADD CONSTRAINT chk_transaction_type
        CHECK (type IN ('PURCHASE', 'PAYOUT', 'REFUND', 'FEE', 'SUBSCRIPTION', 'CREDIT'))
    """)

    op.execute("""
        ALTER TABLE transactions
        ADD CONSTRAINT chk_transaction_status
        CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'REFUNDED', 'DISPUTED'))
    """)

    op.execute("""
        ALTER TABLE transactions
        ADD CONSTRAINT chk_transaction_amount_nonzero
        CHECK (amount_usd != 0)
    """)

    # ============================================================
    # SECTION 7: Listings - Add FK CASCADE and constraints
    # ============================================================

    # Drop and recreate FK with ON DELETE CASCADE
    op.drop_constraint('listings_identity_id_fkey', 'listings', type_='foreignkey')
    op.create_foreign_key(
        'listings_identity_id_fkey',
        'listings', 'identities',
        ['identity_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE listings
        ADD CONSTRAINT chk_listing_category
        CHECK (category IS NULL OR category IN ('ACTOR', 'MODEL', 'INFLUENCER', 'CHARACTER', 'PRESENTER', 'VOICE', 'VOICE_ARTIST', 'CUSTOM'))
    """)

    op.execute("""
        ALTER TABLE listings
        ADD CONSTRAINT chk_listing_view_count_positive
        CHECK (view_count >= 0)
    """)

    op.execute("""
        ALTER TABLE listings
        ADD CONSTRAINT chk_listing_favorite_count_positive
        CHECK (favorite_count >= 0)
    """)

    op.execute("""
        ALTER TABLE listings
        ADD CONSTRAINT chk_listing_license_count_positive
        CHECK (license_count >= 0)
    """)

    op.execute("""
        ALTER TABLE listings
        ADD CONSTRAINT chk_listing_rating_count_positive
        CHECK (rating_count >= 0)
    """)

    op.execute("""
        ALTER TABLE listings
        ADD CONSTRAINT chk_listing_avg_rating_range
        CHECK (avg_rating IS NULL OR (avg_rating >= 0 AND avg_rating <= 5))
    """)

    # One active listing per identity
    op.create_index(
        'idx_listing_identity_unique_active',
        'listings',
        ['identity_id'],
        unique=True,
        postgresql_where='is_active = true'
    )

    # Additional indexes
    op.create_index('idx_listing_category_active', 'listings', ['category', 'is_active'])
    op.create_index('idx_listing_featured', 'listings', ['is_featured', 'is_active'])

    # ============================================================
    # SECTION 8: Usage Logs - Add FK SET NULL and constraints
    # ============================================================

    # Drop and recreate FKs with ON DELETE SET NULL
    op.drop_constraint('usage_logs_identity_id_fkey', 'usage_logs', type_='foreignkey')
    op.create_foreign_key(
        'usage_logs_identity_id_fkey',
        'usage_logs', 'identities',
        ['identity_id'], ['id'],
        ondelete='SET NULL'
    )

    op.drop_constraint('usage_logs_license_id_fkey', 'usage_logs', type_='foreignkey')
    op.create_foreign_key(
        'usage_logs_license_id_fkey',
        'usage_logs', 'licenses',
        ['license_id'], ['id'],
        ondelete='SET NULL'
    )

    op.drop_constraint('usage_logs_actor_pack_id_fkey', 'usage_logs', type_='foreignkey')
    op.create_foreign_key(
        'usage_logs_actor_pack_id_fkey',
        'usage_logs', 'actor_packs',
        ['actor_pack_id'], ['id'],
        ondelete='SET NULL'
    )

    op.drop_constraint('usage_logs_api_key_id_fkey', 'usage_logs', type_='foreignkey')
    op.create_foreign_key(
        'usage_logs_api_key_id_fkey',
        'usage_logs', 'api_keys',
        ['api_key_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE usage_logs
        ADD CONSTRAINT chk_usage_log_response_time_positive
        CHECK (response_time_ms IS NULL OR response_time_ms >= 0)
    """)

    op.execute("""
        ALTER TABLE usage_logs
        ADD CONSTRAINT chk_usage_log_similarity_range
        CHECK (similarity_score IS NULL OR (similarity_score >= 0 AND similarity_score <= 1))
    """)

    op.execute("""
        ALTER TABLE usage_logs
        ADD CONSTRAINT chk_usage_log_credits_positive
        CHECK (credits_used >= 0)
    """)

    op.execute("""
        ALTER TABLE usage_logs
        ADD CONSTRAINT chk_usage_log_amount_positive
        CHECK (amount_charged_usd >= 0)
    """)

    op.execute("""
        ALTER TABLE usage_logs
        ADD CONSTRAINT chk_usage_log_faces_positive
        CHECK (faces_detected IS NULL OR faces_detected >= 0)
    """)

    # Add indexes for analytics
    op.create_index('idx_usage_identity_date', 'usage_logs', ['identity_id', 'created_at'])
    op.create_index('idx_usage_action_date', 'usage_logs', ['action', 'created_at'])
    op.create_index('idx_usage_requester', 'usage_logs', ['requester_id', 'created_at'])

    # ============================================================
    # SECTION 9: Notifications - Add FK CASCADE and constraints
    # ============================================================

    # Drop and recreate FK with ON DELETE CASCADE
    op.drop_constraint('notifications_user_id_fkey', 'notifications', type_='foreignkey')
    op.create_foreign_key(
        'notifications_user_id_fkey',
        'notifications', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE notifications
        ADD CONSTRAINT chk_notification_expires_after_created
        CHECK (expires_at IS NULL OR expires_at > created_at)
    """)

    op.execute("""
        ALTER TABLE notifications
        ADD CONSTRAINT chk_notification_read_after_created
        CHECK (read_at IS NULL OR read_at >= created_at)
    """)

    op.execute("""
        ALTER TABLE notifications
        ADD CONSTRAINT chk_notification_sent_after_created
        CHECK (sent_at IS NULL OR sent_at >= created_at)
    """)

    # Partial index for unread notifications
    op.create_index(
        'idx_notification_user_unread',
        'notifications',
        ['user_id', 'is_read'],
        postgresql_where='is_read = false'
    )

    # ============================================================
    # SECTION 10: Audit Logs - Add FK SET NULL and constraints
    # ============================================================

    # Drop and recreate FKs with ON DELETE SET NULL
    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')
    op.create_foreign_key(
        'audit_logs_user_id_fkey',
        'audit_logs', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )

    op.drop_constraint('audit_logs_api_key_id_fkey', 'audit_logs', type_='foreignkey')
    op.create_foreign_key(
        'audit_logs_api_key_id_fkey',
        'audit_logs', 'api_keys',
        ['api_key_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE audit_logs
        ADD CONSTRAINT chk_audit_log_request_method
        CHECK (request_method IS NULL OR request_method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'))
    """)

    # Add indexes for compliance queries
    op.create_index('idx_audit_log_user_action', 'audit_logs', ['user_id', 'action', 'created_at'])
    op.create_index('idx_audit_log_resource', 'audit_logs', ['resource_type', 'resource_id', 'created_at'])

    # ============================================================
    # SECTION 11: Webhook Events - Add constraints
    # ============================================================

    op.execute("""
        ALTER TABLE webhook_events
        ADD CONSTRAINT chk_webhook_attempts_positive
        CHECK (attempts >= 0)
    """)

    op.execute("""
        ALTER TABLE webhook_events
        ADD CONSTRAINT chk_webhook_processed_after_created
        CHECK (processed_at IS NULL OR processed_at >= created_at)
    """)

    op.execute("""
        ALTER TABLE webhook_events
        ADD CONSTRAINT chk_webhook_attempt_after_created
        CHECK (last_attempt_at IS NULL OR last_attempt_at >= created_at)
    """)

    # Index for cleanup queries
    op.create_index('idx_webhook_status_created', 'webhook_events', ['status', 'created_at'])

    # ============================================================
    # SECTION 12: Subscriptions - Add FK CASCADE and constraints
    # ============================================================

    # Drop and recreate FK with ON DELETE CASCADE
    op.drop_constraint('subscriptions_user_id_fkey', 'subscriptions', type_='foreignkey')
    op.create_foreign_key(
        'subscriptions_user_id_fkey',
        'subscriptions', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE subscriptions
        ADD CONSTRAINT chk_subscription_amount_positive
        CHECK (amount >= 0)
    """)

    op.execute("""
        ALTER TABLE subscriptions
        ADD CONSTRAINT chk_subscription_interval_valid
        CHECK (interval IS NULL OR interval IN ('month', 'year'))
    """)

    op.execute("""
        ALTER TABLE subscriptions
        ADD CONSTRAINT chk_subscription_identities_limit_positive
        CHECK (identities_limit > 0)
    """)

    op.execute("""
        ALTER TABLE subscriptions
        ADD CONSTRAINT chk_subscription_api_calls_limit_positive
        CHECK (api_calls_limit > 0)
    """)

    op.execute("""
        ALTER TABLE subscriptions
        ADD CONSTRAINT chk_subscription_storage_limit_positive
        CHECK (storage_limit_mb > 0)
    """)

    op.execute("""
        ALTER TABLE subscriptions
        ADD CONSTRAINT chk_subscription_period_valid
        CHECK (current_period_end IS NULL OR current_period_start IS NULL OR current_period_end >= current_period_start)
    """)

    op.execute("""
        ALTER TABLE subscriptions
        ADD CONSTRAINT chk_subscription_trial_period_valid
        CHECK (trial_end IS NULL OR trial_start IS NULL OR trial_end >= trial_start)
    """)

    # One active subscription per user
    op.create_index(
        'idx_subscription_user_active_unique',
        'subscriptions',
        ['user_id'],
        unique=True,
        postgresql_where="status IN ('ACTIVE', 'TRIALING', 'PAST_DUE')"
    )

    # ============================================================
    # SECTION 13: Payouts - Add FK SET NULL and constraints
    # ============================================================

    # Drop and recreate FK with ON DELETE SET NULL (preserve financial records)
    op.drop_constraint('payouts_user_id_fkey', 'payouts', type_='foreignkey')
    op.create_foreign_key(
        'payouts_user_id_fkey',
        'payouts', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )

    # Make user_id nullable for SET NULL to work
    op.alter_column('payouts', 'user_id', nullable=True)

    # Add CHECK constraints
    op.execute("""
        ALTER TABLE payouts
        ADD CONSTRAINT chk_payout_amount_positive
        CHECK (amount > 0)
    """)

    op.execute("""
        ALTER TABLE payouts
        ADD CONSTRAINT chk_payout_fee_positive
        CHECK (fee >= 0)
    """)

    op.execute("""
        ALTER TABLE payouts
        ADD CONSTRAINT chk_payout_net_amount_positive
        CHECK (net_amount IS NULL OR net_amount >= 0)
    """)

    op.execute("""
        ALTER TABLE payouts
        ADD CONSTRAINT chk_payout_net_amount_valid
        CHECK (net_amount IS NULL OR (net_amount <= amount AND net_amount = amount - fee))
    """)

    op.execute("""
        ALTER TABLE payouts
        ADD CONSTRAINT chk_payout_transaction_count_positive
        CHECK (transaction_count >= 0)
    """)

    op.execute("""
        ALTER TABLE payouts
        ADD CONSTRAINT chk_payout_period_valid
        CHECK (period_end IS NULL OR period_start IS NULL OR period_end >= period_start)
    """)

    op.execute("""
        ALTER TABLE payouts
        ADD CONSTRAINT chk_payout_processed_after_requested
        CHECK (processed_at IS NULL OR processed_at >= requested_at)
    """)

    op.execute("""
        ALTER TABLE payouts
        ADD CONSTRAINT chk_payout_completed_after_processed
        CHECK (completed_at IS NULL OR (processed_at IS NOT NULL AND completed_at >= processed_at))
    """)

    # Add indexes
    op.create_index('idx_payout_user_status', 'payouts', ['user_id', 'status'])
    op.create_index('idx_payout_period', 'payouts', ['period_start', 'period_end'])


def downgrade():
    """Remove all data integrity constraints"""

    # Drop payout constraints and indexes
    op.drop_index('idx_payout_period', table_name='payouts')
    op.drop_index('idx_payout_user_status', table_name='payouts')
    op.execute('ALTER TABLE payouts DROP CONSTRAINT IF EXISTS chk_payout_completed_after_processed')
    op.execute('ALTER TABLE payouts DROP CONSTRAINT IF EXISTS chk_payout_processed_after_requested')
    op.execute('ALTER TABLE payouts DROP CONSTRAINT IF EXISTS chk_payout_period_valid')
    op.execute('ALTER TABLE payouts DROP CONSTRAINT IF EXISTS chk_payout_transaction_count_positive')
    op.execute('ALTER TABLE payouts DROP CONSTRAINT IF EXISTS chk_payout_net_amount_valid')
    op.execute('ALTER TABLE payouts DROP CONSTRAINT IF EXISTS chk_payout_net_amount_positive')
    op.execute('ALTER TABLE payouts DROP CONSTRAINT IF EXISTS chk_payout_fee_positive')
    op.execute('ALTER TABLE payouts DROP CONSTRAINT IF EXISTS chk_payout_amount_positive')
    op.alter_column('payouts', 'user_id', nullable=False)
    op.drop_constraint('payouts_user_id_fkey', 'payouts', type_='foreignkey')
    op.create_foreign_key('payouts_user_id_fkey', 'payouts', 'users', ['user_id'], ['id'])

    # Drop subscription constraints and indexes
    op.drop_index('idx_subscription_user_active_unique', table_name='subscriptions')
    op.execute('ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS chk_subscription_trial_period_valid')
    op.execute('ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS chk_subscription_period_valid')
    op.execute('ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS chk_subscription_storage_limit_positive')
    op.execute('ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS chk_subscription_api_calls_limit_positive')
    op.execute('ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS chk_subscription_identities_limit_positive')
    op.execute('ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS chk_subscription_interval_valid')
    op.execute('ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS chk_subscription_amount_positive')
    op.drop_constraint('subscriptions_user_id_fkey', 'subscriptions', type_='foreignkey')
    op.create_foreign_key('subscriptions_user_id_fkey', 'subscriptions', 'users', ['user_id'], ['id'])

    # Drop webhook_events constraints and indexes
    op.drop_index('idx_webhook_status_created', table_name='webhook_events')
    op.execute('ALTER TABLE webhook_events DROP CONSTRAINT IF EXISTS chk_webhook_attempt_after_created')
    op.execute('ALTER TABLE webhook_events DROP CONSTRAINT IF EXISTS chk_webhook_processed_after_created')
    op.execute('ALTER TABLE webhook_events DROP CONSTRAINT IF EXISTS chk_webhook_attempts_positive')

    # Drop audit_logs constraints and indexes
    op.drop_index('idx_audit_log_resource', table_name='audit_logs')
    op.drop_index('idx_audit_log_user_action', table_name='audit_logs')
    op.execute('ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS chk_audit_log_request_method')
    op.drop_constraint('audit_logs_api_key_id_fkey', 'audit_logs', type_='foreignkey')
    op.create_foreign_key('audit_logs_api_key_id_fkey', 'audit_logs', 'api_keys', ['api_key_id'], ['id'])
    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')
    op.create_foreign_key('audit_logs_user_id_fkey', 'audit_logs', 'users', ['user_id'], ['id'])

    # Drop notification constraints and indexes
    op.drop_index('idx_notification_user_unread', table_name='notifications')
    op.execute('ALTER TABLE notifications DROP CONSTRAINT IF EXISTS chk_notification_sent_after_created')
    op.execute('ALTER TABLE notifications DROP CONSTRAINT IF EXISTS chk_notification_read_after_created')
    op.execute('ALTER TABLE notifications DROP CONSTRAINT IF EXISTS chk_notification_expires_after_created')
    op.drop_constraint('notifications_user_id_fkey', 'notifications', type_='foreignkey')
    op.create_foreign_key('notifications_user_id_fkey', 'notifications', 'users', ['user_id'], ['id'])

    # Drop usage_logs constraints and indexes
    op.drop_index('idx_usage_requester', table_name='usage_logs')
    op.drop_index('idx_usage_action_date', table_name='usage_logs')
    op.drop_index('idx_usage_identity_date', table_name='usage_logs')
    op.execute('ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS chk_usage_log_faces_positive')
    op.execute('ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS chk_usage_log_amount_positive')
    op.execute('ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS chk_usage_log_credits_positive')
    op.execute('ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS chk_usage_log_similarity_range')
    op.execute('ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS chk_usage_log_response_time_positive')
    op.drop_constraint('usage_logs_api_key_id_fkey', 'usage_logs', type_='foreignkey')
    op.create_foreign_key('usage_logs_api_key_id_fkey', 'usage_logs', 'api_keys', ['api_key_id'], ['id'])
    op.drop_constraint('usage_logs_actor_pack_id_fkey', 'usage_logs', type_='foreignkey')
    op.create_foreign_key('usage_logs_actor_pack_id_fkey', 'usage_logs', 'actor_packs', ['actor_pack_id'], ['id'])
    op.drop_constraint('usage_logs_license_id_fkey', 'usage_logs', type_='foreignkey')
    op.create_foreign_key('usage_logs_license_id_fkey', 'usage_logs', 'licenses', ['license_id'], ['id'])
    op.drop_constraint('usage_logs_identity_id_fkey', 'usage_logs', type_='foreignkey')
    op.create_foreign_key('usage_logs_identity_id_fkey', 'usage_logs', 'identities', ['identity_id'], ['id'])

    # Drop listing constraints and indexes
    op.drop_index('idx_listing_featured', table_name='listings')
    op.drop_index('idx_listing_category_active', table_name='listings')
    op.drop_index('idx_listing_identity_unique_active', table_name='listings')
    op.execute('ALTER TABLE listings DROP CONSTRAINT IF EXISTS chk_listing_avg_rating_range')
    op.execute('ALTER TABLE listings DROP CONSTRAINT IF EXISTS chk_listing_rating_count_positive')
    op.execute('ALTER TABLE listings DROP CONSTRAINT IF EXISTS chk_listing_license_count_positive')
    op.execute('ALTER TABLE listings DROP CONSTRAINT IF EXISTS chk_listing_favorite_count_positive')
    op.execute('ALTER TABLE listings DROP CONSTRAINT IF EXISTS chk_listing_view_count_positive')
    op.execute('ALTER TABLE listings DROP CONSTRAINT IF EXISTS chk_listing_category')
    op.drop_constraint('listings_identity_id_fkey', 'listings', type_='foreignkey')
    op.create_foreign_key('listings_identity_id_fkey', 'listings', 'identities', ['identity_id'], ['id'])

    # Drop transaction constraints
    op.execute('ALTER TABLE transactions DROP CONSTRAINT IF EXISTS chk_transaction_amount_nonzero')
    op.execute('ALTER TABLE transactions DROP CONSTRAINT IF EXISTS chk_transaction_status')
    op.execute('ALTER TABLE transactions DROP CONSTRAINT IF EXISTS chk_transaction_type')
    op.drop_constraint('transactions_user_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key('transactions_user_id_fkey', 'transactions', 'users', ['user_id'], ['id'])
    op.drop_constraint('transactions_license_id_fkey', 'transactions', type_='foreignkey')
    op.create_foreign_key('transactions_license_id_fkey', 'transactions', 'licenses', ['license_id'], ['id'])

    # Drop license constraints and indexes
    op.drop_index('idx_license_active', table_name='licenses')
    op.drop_index('idx_license_dates', table_name='licenses')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_max_outputs')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_max_impressions')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_dates_valid')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_duration_positive')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_impressions_positive')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_uses_positive')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_fee_percent_range')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_payout_valid')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_price_positive')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_payment_status')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_usage_type')
    op.execute('ALTER TABLE licenses DROP CONSTRAINT IF EXISTS chk_license_type')
    op.drop_constraint('licenses_licensee_id_fkey', 'licenses', type_='foreignkey')
    op.create_foreign_key('licenses_licensee_id_fkey', 'licenses', 'users', ['licensee_id'], ['id'])
    op.drop_constraint('licenses_identity_id_fkey', 'licenses', type_='foreignkey')
    op.create_foreign_key('licenses_identity_id_fkey', 'licenses', 'identities', ['identity_id'], ['id'])

    # Drop actor_packs constraints
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_file_size_positive')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_rating_count_positive')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_revenue_positive')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_uses_positive')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_downloads_positive')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_price_per_image_positive')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_price_per_second_positive')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_base_price_positive')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_voice_quality_range')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_consistency_range')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_authenticity_range')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_quality_range')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_progress_range')
    op.execute('ALTER TABLE actor_packs DROP CONSTRAINT IF EXISTS chk_actor_pack_training_status')
    op.drop_constraint('actor_packs_identity_id_fkey', 'actor_packs', type_='foreignkey')
    op.create_foreign_key('actor_packs_identity_id_fkey', 'actor_packs', 'identities', ['identity_id'], ['id'])

    # Drop identity constraints and indexes
    op.drop_index('idx_identity_not_deleted', table_name='identities')
    op.drop_index('idx_identity_commercial', table_name='identities')
    op.drop_index('idx_identity_user_status', table_name='identities')
    op.drop_index('idx_identity_user_display_name_unique', table_name='identities')
    op.execute('ALTER TABLE identities DROP CONSTRAINT IF EXISTS chk_identity_total_revenue_positive')
    op.execute('ALTER TABLE identities DROP CONSTRAINT IF EXISTS chk_identity_total_licenses_positive')
    op.execute('ALTER TABLE identities DROP CONSTRAINT IF EXISTS chk_identity_total_verifications_positive')
    op.execute('ALTER TABLE identities DROP CONSTRAINT IF EXISTS chk_identity_revenue_share_range')
    op.execute('ALTER TABLE identities DROP CONSTRAINT IF EXISTS chk_identity_per_image_rate_positive')
    op.execute('ALTER TABLE identities DROP CONSTRAINT IF EXISTS chk_identity_hourly_rate_positive')
    op.execute('ALTER TABLE identities DROP CONSTRAINT IF EXISTS chk_identity_base_fee_positive')
    op.execute('ALTER TABLE identities DROP CONSTRAINT IF EXISTS chk_identity_protection_level')
    op.execute('ALTER TABLE identities DROP CONSTRAINT IF EXISTS chk_identity_status')
    op.drop_constraint('identities_user_id_fkey', 'identities', type_='foreignkey')
    op.create_foreign_key('identities_user_id_fkey', 'identities', 'users', ['user_id'], ['id'])

    # Drop api_keys constraints and indexes
    op.drop_index('idx_apikey_user_name_unique', table_name='api_keys')
    op.execute('ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS chk_apikey_usage_count_positive')
    op.execute('ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS chk_apikey_rate_limit_positive')
    op.drop_constraint('api_keys_user_id_fkey', 'api_keys', type_='foreignkey')
    op.create_foreign_key('api_keys_user_id_fkey', 'api_keys', 'users', ['user_id'], ['id'])

    # Drop user constraints and indexes
    op.drop_index('idx_user_email_active', table_name='users')
    op.drop_index('idx_user_not_deleted', table_name='users')
    op.execute('ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_user_email_format')
    op.execute('ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_user_tier')
    op.execute('ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_user_role')
    op.drop_column('users', 'deleted_at')
