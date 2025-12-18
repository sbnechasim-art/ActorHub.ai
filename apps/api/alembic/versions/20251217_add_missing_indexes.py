"""Add missing database indexes for performance

Revision ID: 20251217_indexes
Revises:
Create Date: 2025-12-17

This migration adds indexes identified during the security audit:
- P1: Performance-critical indexes for commonly queried columns
- P3: Composite indexes for analytics queries
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251217_indexes'
down_revision = '91fd970f8f07'  # Previous migration head
branch_labels = None
depends_on = None


def upgrade():
    """Add missing indexes for performance optimization"""

    # ========================================
    # Users table indexes
    # ========================================
    op.create_index(
        'ix_users_is_active',
        'users',
        ['is_active'],
        if_not_exists=True
    )
    op.create_index(
        'ix_users_tier',
        'users',
        ['tier'],
        if_not_exists=True
    )
    op.create_index(
        'ix_users_created_at',
        'users',
        ['created_at'],
        if_not_exists=True
    )
    op.create_index(
        'ix_users_stripe_customer_id',
        'users',
        ['stripe_customer_id'],
        if_not_exists=True
    )

    # ========================================
    # API Keys table indexes
    # ========================================
    op.create_index(
        'ix_api_keys_user_id',
        'api_keys',
        ['user_id'],
        if_not_exists=True
    )

    # ========================================
    # Identities table indexes
    # ========================================
    op.create_index(
        'ix_identities_deleted_at',
        'identities',
        ['deleted_at'],
        if_not_exists=True
    )

    # ========================================
    # Usage Logs table indexes
    # ========================================
    op.create_index(
        'ix_usage_logs_actor_pack_id',
        'usage_logs',
        ['actor_pack_id'],
        if_not_exists=True
    )
    op.create_index(
        'ix_usage_logs_api_key_id',
        'usage_logs',
        ['api_key_id'],
        if_not_exists=True
    )
    # Composite index for analytics queries
    op.create_index(
        'ix_usage_logs_analytics',
        'usage_logs',
        ['identity_id', 'action', 'created_at'],
        if_not_exists=True
    )

    # ========================================
    # Licenses table indexes
    # ========================================
    op.create_index(
        'ix_licenses_created_at',
        'licenses',
        ['created_at'],
        if_not_exists=True
    )
    op.create_index(
        'ix_licenses_payment_status',
        'licenses',
        ['payment_status'],
        if_not_exists=True
    )

    # ========================================
    # Transactions table indexes
    # ========================================
    op.create_index(
        'ix_transactions_created_at',
        'transactions',
        ['created_at'],
        if_not_exists=True
    )
    op.create_index(
        'ix_transactions_type',
        'transactions',
        ['type'],
        if_not_exists=True
    )
    op.create_index(
        'ix_transactions_stripe_payment_intent_id',
        'transactions',
        ['stripe_payment_intent_id'],
        if_not_exists=True
    )
    # Composite index for financial analytics
    op.create_index(
        'ix_transactions_analytics',
        'transactions',
        ['user_id', 'created_at', 'type'],
        if_not_exists=True
    )


def downgrade():
    """Remove the indexes"""

    # Transactions
    op.drop_index('ix_transactions_analytics', table_name='transactions')
    op.drop_index('ix_transactions_stripe_payment_intent_id', table_name='transactions')
    op.drop_index('ix_transactions_type', table_name='transactions')
    op.drop_index('ix_transactions_created_at', table_name='transactions')

    # Licenses
    op.drop_index('ix_licenses_payment_status', table_name='licenses')
    op.drop_index('ix_licenses_created_at', table_name='licenses')

    # Usage Logs
    op.drop_index('ix_usage_logs_analytics', table_name='usage_logs')
    op.drop_index('ix_usage_logs_api_key_id', table_name='usage_logs')
    op.drop_index('ix_usage_logs_actor_pack_id', table_name='usage_logs')

    # Identities
    op.drop_index('ix_identities_deleted_at', table_name='identities')

    # API Keys
    op.drop_index('ix_api_keys_user_id', table_name='api_keys')

    # Users
    op.drop_index('ix_users_stripe_customer_id', table_name='users')
    op.drop_index('ix_users_created_at', table_name='users')
    op.drop_index('ix_users_tier', table_name='users')
    op.drop_index('ix_users_is_active', table_name='users')
