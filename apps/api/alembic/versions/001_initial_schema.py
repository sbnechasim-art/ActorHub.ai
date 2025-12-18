"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255)),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('display_name', sa.String(100)),
        sa.Column('avatar_url', sa.Text),
        sa.Column('clerk_user_id', sa.String(255), unique=True, index=True),
        sa.Column('email_verified', sa.Boolean, default=False),
        sa.Column('phone_number', sa.String(20)),
        sa.Column('phone_verified', sa.Boolean, default=False),
        sa.Column('role', sa.String(20), default='user'),
        sa.Column('tier', sa.String(20), default='free'),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_verified', sa.Boolean, default=False),
        sa.Column('stripe_customer_id', sa.String(255)),
        sa.Column('billing_email', sa.String(255)),
        sa.Column('preferences', postgresql.JSONB, default=dict),
        sa.Column('notification_settings', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime),
    )

    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_hash', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('key_prefix', sa.String(10)),
        sa.Column('permissions', postgresql.JSONB, default=list),
        sa.Column('allowed_ips', postgresql.JSONB),
        sa.Column('rate_limit', sa.Integer, default=100),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('expires_at', sa.DateTime),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('last_used_at', sa.DateTime),
        sa.Column('last_used_ip', sa.String(50)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Identities table
    op.create_table(
        'identities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('legal_name', sa.String(255)),
        sa.Column('bio', sa.Text),
        sa.Column('profile_image_url', sa.Text),
        sa.Column('status', sa.String(20), default='pending', index=True),
        sa.Column('verified_at', sa.DateTime),
        sa.Column('verification_method', sa.String(50)),
        sa.Column('verification_data', postgresql.JSONB),
        sa.Column('face_embedding', postgresql.ARRAY(sa.Float)),
        sa.Column('face_embedding_backup', postgresql.ARRAY(sa.Float)),
        sa.Column('protection_level', sa.String(20), default='free'),
        sa.Column('allow_commercial_use', sa.Boolean, default=False),
        sa.Column('allow_ai_training', sa.Boolean, default=False),
        sa.Column('allow_deepfake', sa.Boolean, default=False),
        sa.Column('blocked_categories', postgresql.ARRAY(sa.String), default=list),
        sa.Column('blocked_brands', postgresql.ARRAY(sa.String), default=list),
        sa.Column('blocked_regions', postgresql.ARRAY(sa.String), default=list),
        sa.Column('custom_restrictions', postgresql.JSONB, default=dict),
        sa.Column('base_license_fee', sa.Float, default=0),
        sa.Column('hourly_rate', sa.Float, default=0),
        sa.Column('per_image_rate', sa.Float, default=0),
        sa.Column('revenue_share_percent', sa.Float, default=70),
        sa.Column('nft_token_id', sa.String(100)),
        sa.Column('nft_contract_address', sa.String(100)),
        sa.Column('nft_minted_at', sa.DateTime),
        sa.Column('blockchain_hash', sa.String(100)),
        sa.Column('total_verifications', sa.Integer, default=0),
        sa.Column('total_licenses', sa.Integer, default=0),
        sa.Column('total_revenue', sa.Float, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime),
    )

    # Actor Packs table
    op.create_table(
        'actor_packs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identities.id'), unique=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('version', sa.String(20), default='1.0.0'),
        sa.Column('slug', sa.String(100), unique=True),
        sa.Column('training_status', sa.String(20), default='pending'),
        sa.Column('training_started_at', sa.DateTime),
        sa.Column('training_completed_at', sa.DateTime),
        sa.Column('training_error', sa.Text),
        sa.Column('training_progress', sa.Integer, default=0),
        sa.Column('training_images_count', sa.Integer, default=0),
        sa.Column('training_audio_seconds', sa.Float, default=0),
        sa.Column('training_video_seconds', sa.Float, default=0),
        sa.Column('quality_score', sa.Float),
        sa.Column('authenticity_score', sa.Float),
        sa.Column('consistency_score', sa.Float),
        sa.Column('voice_quality_score', sa.Float),
        sa.Column('s3_bucket', sa.String(255)),
        sa.Column('s3_key', sa.String(500)),
        sa.Column('file_size_bytes', sa.Float),
        sa.Column('checksum', sa.String(64)),
        sa.Column('components', postgresql.JSONB, default=dict),
        sa.Column('lora_model_url', sa.Text),
        sa.Column('voice_model_id', sa.String(255)),
        sa.Column('motion_data_url', sa.Text),
        sa.Column('base_price_usd', sa.Float, default=0),
        sa.Column('price_per_second_usd', sa.Float, default=0),
        sa.Column('price_per_image_usd', sa.Float, default=0),
        sa.Column('total_downloads', sa.Integer, default=0),
        sa.Column('total_uses', sa.Integer, default=0),
        sa.Column('total_revenue_usd', sa.Float, default=0),
        sa.Column('avg_rating', sa.Float),
        sa.Column('rating_count', sa.Integer, default=0),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('is_available', sa.Boolean, default=True),
        sa.Column('requires_approval', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Licenses table
    op.create_table(
        'licenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identities.id'), nullable=False, index=True),
        sa.Column('licensee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('license_type', sa.String(20), nullable=False),
        sa.Column('usage_type', sa.String(20), nullable=False),
        sa.Column('project_name', sa.String(255)),
        sa.Column('project_description', sa.Text),
        sa.Column('allowed_platforms', postgresql.ARRAY(sa.String)),
        sa.Column('allowed_regions', postgresql.ARRAY(sa.String)),
        sa.Column('excluded_uses', postgresql.ARRAY(sa.String)),
        sa.Column('max_impressions', sa.Integer),
        sa.Column('max_duration_seconds', sa.Integer),
        sa.Column('max_images', sa.Integer),
        sa.Column('max_outputs', sa.Integer),
        sa.Column('valid_from', sa.DateTime, nullable=False),
        sa.Column('valid_until', sa.DateTime),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('auto_renew', sa.Boolean, default=False),
        sa.Column('price_usd', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('payment_status', sa.String(20), default='pending'),
        sa.Column('stripe_payment_intent_id', sa.String(255)),
        sa.Column('stripe_subscription_id', sa.String(255)),
        sa.Column('paid_at', sa.DateTime),
        sa.Column('platform_fee_percent', sa.Float, default=20),
        sa.Column('creator_payout_usd', sa.Float),
        sa.Column('payout_status', sa.String(50), default='pending'),
        sa.Column('payout_at', sa.DateTime),
        sa.Column('contract_hash', sa.String(100)),
        sa.Column('contract_url', sa.Text),
        sa.Column('signed_at', sa.DateTime),
        sa.Column('terms_accepted', sa.Boolean, default=False),
        sa.Column('current_uses', sa.Integer, default=0),
        sa.Column('current_impressions', sa.Integer, default=0),
        sa.Column('current_duration_seconds', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('license_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('licenses.id'), index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('amount_usd', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('description', sa.Text),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('stripe_payment_intent_id', sa.String(255)),
        sa.Column('stripe_charge_id', sa.String(255)),
        sa.Column('stripe_transfer_id', sa.String(255)),
        sa.Column('transaction_metadata', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
        sa.Column('completed_at', sa.DateTime),
    )

    # Listings table
    op.create_table(
        'listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identities.id'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True),
        sa.Column('description', sa.Text),
        sa.Column('short_description', sa.String(500)),
        sa.Column('thumbnail_url', sa.Text),
        sa.Column('preview_images', postgresql.ARRAY(sa.Text)),
        sa.Column('preview_video_url', sa.Text),
        sa.Column('demo_audio_url', sa.Text),
        sa.Column('category', sa.String(100)),
        sa.Column('tags', postgresql.ARRAY(sa.String)),
        sa.Column('style_tags', postgresql.ARRAY(sa.String)),
        sa.Column('pricing_tiers', postgresql.JSONB, default=list),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_featured', sa.Boolean, default=False),
        sa.Column('requires_approval', sa.Boolean, default=False),
        sa.Column('view_count', sa.Integer, default=0),
        sa.Column('favorite_count', sa.Integer, default=0),
        sa.Column('license_count', sa.Integer, default=0),
        sa.Column('avg_rating', sa.Float),
        sa.Column('rating_count', sa.Integer, default=0),
        sa.Column('meta_title', sa.String(255)),
        sa.Column('meta_description', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('published_at', sa.DateTime),
    )

    # Usage Logs table
    op.create_table(
        'usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('identity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('identities.id'), index=True),
        sa.Column('license_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('licenses.id'), index=True),
        sa.Column('actor_pack_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('actor_packs.id')),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), index=True),
        sa.Column('requester_type', sa.String(50)),
        sa.Column('requester_name', sa.String(255)),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id')),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('endpoint', sa.String(255)),
        sa.Column('request_metadata', postgresql.JSONB),
        sa.Column('similarity_score', sa.Float),
        sa.Column('faces_detected', sa.Integer),
        sa.Column('matched', sa.Boolean),
        sa.Column('result', sa.String(50)),
        sa.Column('result_reason', sa.Text),
        sa.Column('response_time_ms', sa.Integer),
        sa.Column('credits_used', sa.Float, default=0),
        sa.Column('amount_charged_usd', sa.Float, default=0),
        sa.Column('billed', sa.Boolean, default=False),
        sa.Column('ip_address', sa.String(50)),
        sa.Column('user_agent', sa.Text),
        sa.Column('country_code', sa.String(2)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), index=True),
    )

    # Create indexes
    op.create_index('idx_identity_user_status', 'identities', ['user_id', 'status'])
    op.create_index('idx_identity_commercial', 'identities', ['allow_commercial_use', 'status'])
    op.create_index('idx_license_dates', 'licenses', ['valid_from', 'valid_until'])
    op.create_index('idx_license_active', 'licenses', ['is_active', 'valid_until'])
    op.create_index('idx_listing_category_active', 'listings', ['category', 'is_active'])
    op.create_index('idx_listing_featured', 'listings', ['is_featured', 'is_active'])
    op.create_index('idx_usage_identity_date', 'usage_logs', ['identity_id', 'created_at'])
    op.create_index('idx_usage_action_date', 'usage_logs', ['action', 'created_at'])
    op.create_index('idx_usage_requester', 'usage_logs', ['requester_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('usage_logs')
    op.drop_table('listings')
    op.drop_table('transactions')
    op.drop_table('licenses')
    op.drop_table('actor_packs')
    op.drop_table('identities')
    op.drop_table('api_keys')
    op.drop_table('users')
