"""Add notifications, audit_logs, webhook_events, subscriptions, and payouts tables

Revision ID: 20251218_notifications
Revises: 20251217_indexes
Create Date: 2025-12-18

Adds missing tables identified during system audit:
- notifications: User notification system
- audit_logs: Security and compliance audit trail
- webhook_events: Webhook idempotency and tracking
- subscriptions: User billing subscriptions
- payouts: Creator marketplace payouts
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251218_notifications'
down_revision = '20251217_indexes'
branch_labels = None
depends_on = None


def upgrade():
    """Create new tables"""

    # Create enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationtype AS ENUM (
                'SYSTEM', 'MARKETING', 'SECURITY', 'BILLING',
                'IDENTITY', 'TRAINING', 'DETECTION'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationchannel AS ENUM (
                'IN_APP', 'EMAIL', 'SMS', 'PUSH'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE auditaction AS ENUM (
                'CREATE', 'READ', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT',
                'EXPORT', 'DOWNLOAD', 'VERIFY', 'DETECT', 'TRAIN',
                'PURCHASE', 'REFUND', 'API_CALL'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE webhookstatus AS ENUM (
                'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'RETRYING'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE webhooksource AS ENUM (
                'STRIPE', 'CLERK', 'SENDGRID', 'REPLICATE', 'ELEVENLABS'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE subscriptionstatus AS ENUM (
                'ACTIVE', 'PAST_DUE', 'CANCELED', 'INCOMPLETE', 'TRIALING', 'PAUSED'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE subscriptionplan AS ENUM (
                'FREE', 'PRO_MONTHLY', 'PRO_YEARLY', 'ENTERPRISE_MONTHLY', 'ENTERPRISE_YEARLY'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE payoutstatus AS ENUM (
                'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELED'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE payoutmethod AS ENUM (
                'STRIPE_CONNECT', 'PAYPAL', 'BANK_TRANSFER'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', postgresql.ENUM('SYSTEM', 'MARKETING', 'SECURITY', 'BILLING', 'IDENTITY', 'TRAINING', 'DETECTION', name='notificationtype', create_type=False), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('action_url', sa.Text),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('channel', postgresql.ENUM('IN_APP', 'EMAIL', 'SMS', 'PUSH', name='notificationchannel', create_type=False), default='IN_APP'),
        sa.Column('is_read', sa.Boolean, default=False),
        sa.Column('read_at', sa.DateTime),
        sa.Column('is_sent', sa.Boolean, default=False),
        sa.Column('sent_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_type', 'notifications', ['type'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id')),
        sa.Column('ip_address', sa.String(50)),
        sa.Column('user_agent', sa.Text),
        sa.Column('action', postgresql.ENUM('CREATE', 'READ', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'EXPORT', 'DOWNLOAD', 'VERIFY', 'DETECT', 'TRAIN', 'PURCHASE', 'REFUND', 'API_CALL', name='auditaction', create_type=False), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True)),
        sa.Column('description', sa.Text),
        sa.Column('old_values', postgresql.JSONB),
        sa.Column('new_values', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('request_id', sa.String(64)),
        sa.Column('request_path', sa.Text),
        sa.Column('request_method', sa.String(10)),
        sa.Column('success', sa.Boolean, default=True),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'])
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # Create webhook_events table
    op.create_table(
        'webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('event_id', sa.String(255), nullable=False, unique=True),
        sa.Column('source', postgresql.ENUM('STRIPE', 'CLERK', 'SENDGRID', 'REPLICATE', 'ELEVENLABS', name='webhooksource', create_type=False), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('headers', postgresql.JSONB),
        sa.Column('status', postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'RETRYING', name='webhookstatus', create_type=False), default='PENDING'),
        sa.Column('attempts', sa.Integer, default=0),
        sa.Column('last_attempt_at', sa.DateTime),
        sa.Column('processed_at', sa.DateTime),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_webhook_events_event_id', 'webhook_events', ['event_id'])
    op.create_index('ix_webhook_events_source', 'webhook_events', ['source'])
    op.create_index('ix_webhook_events_event_type', 'webhook_events', ['event_type'])
    op.create_index('ix_webhook_events_status', 'webhook_events', ['status'])
    op.create_index('ix_webhook_events_created_at', 'webhook_events', ['created_at'])

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(255), unique=True),
        sa.Column('stripe_customer_id', sa.String(255)),
        sa.Column('stripe_price_id', sa.String(255)),
        sa.Column('plan', postgresql.ENUM('FREE', 'PRO_MONTHLY', 'PRO_YEARLY', 'ENTERPRISE_MONTHLY', 'ENTERPRISE_YEARLY', name='subscriptionplan', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'PAST_DUE', 'CANCELED', 'INCOMPLETE', 'TRIALING', 'PAUSED', name='subscriptionstatus', create_type=False), nullable=False, default='ACTIVE'),
        sa.Column('amount', sa.Float, default=0.0),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('interval', sa.String(20)),
        sa.Column('current_period_start', sa.DateTime),
        sa.Column('current_period_end', sa.DateTime),
        sa.Column('trial_start', sa.DateTime),
        sa.Column('trial_end', sa.DateTime),
        sa.Column('canceled_at', sa.DateTime),
        sa.Column('cancel_at_period_end', sa.Boolean, default=False),
        sa.Column('identities_limit', sa.Integer, default=3),
        sa.Column('api_calls_limit', sa.Integer, default=1000),
        sa.Column('storage_limit_mb', sa.Integer, default=100),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'])
    op.create_index('ix_subscriptions_stripe_customer_id', 'subscriptions', ['stripe_customer_id'])
    op.create_index('ix_subscriptions_plan', 'subscriptions', ['plan'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])

    # Create payouts table
    op.create_table(
        'payouts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('fee', sa.Float, default=0.0),
        sa.Column('net_amount', sa.Float),
        sa.Column('method', postgresql.ENUM('STRIPE_CONNECT', 'PAYPAL', 'BANK_TRANSFER', name='payoutmethod', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELED', name='payoutstatus', create_type=False), default='PENDING'),
        sa.Column('stripe_payout_id', sa.String(255), unique=True),
        sa.Column('stripe_transfer_id', sa.String(255)),
        sa.Column('period_start', sa.DateTime),
        sa.Column('period_end', sa.DateTime),
        sa.Column('transaction_ids', postgresql.JSONB, default=[]),
        sa.Column('transaction_count', sa.Integer, default=0),
        sa.Column('requested_at', sa.DateTime, default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('failed_at', sa.DateTime),
        sa.Column('failure_reason', sa.Text),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_payouts_user_id', 'payouts', ['user_id'])
    op.create_index('ix_payouts_stripe_payout_id', 'payouts', ['stripe_payout_id'])
    op.create_index('ix_payouts_status', 'payouts', ['status'])


def downgrade():
    """Drop tables"""
    op.drop_table('payouts')
    op.drop_table('subscriptions')
    op.drop_table('webhook_events')
    op.drop_table('audit_logs')
    op.drop_table('notifications')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS payoutmethod')
    op.execute('DROP TYPE IF EXISTS payoutstatus')
    op.execute('DROP TYPE IF EXISTS subscriptionplan')
    op.execute('DROP TYPE IF EXISTS subscriptionstatus')
    op.execute('DROP TYPE IF EXISTS webhooksource')
    op.execute('DROP TYPE IF EXISTS webhookstatus')
    op.execute('DROP TYPE IF EXISTS auditaction')
    op.execute('DROP TYPE IF EXISTS notificationchannel')
    op.execute('DROP TYPE IF EXISTS notificationtype')
