"""add_2fa_and_gdpr_fields_to_users

Revision ID: 91fd970f8f07
Revises: 001
Create Date: 2025-12-16 20:37:21.799047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '91fd970f8f07'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only add new columns to users table (skip enum type changes)
    op.add_column('users', sa.Column('verified_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('totp_secret', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('backup_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('is_2fa_enabled', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('email_verification_token', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('email_verification_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('consent_marketing', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('consent_analytics', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('consent_third_party', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('consent_ai_training', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('consent_updated_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('terms_accepted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('privacy_accepted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('cookie_consent', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('cookie_consent_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('age_verified', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('age_verified_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_export_request', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('deletion_requested_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('deletion_scheduled_for', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'deletion_scheduled_for')
    op.drop_column('users', 'deletion_requested_at')
    op.drop_column('users', 'last_export_request')
    op.drop_column('users', 'age_verified_at')
    op.drop_column('users', 'age_verified')
    op.drop_column('users', 'cookie_consent_at')
    op.drop_column('users', 'cookie_consent')
    op.drop_column('users', 'privacy_accepted_at')
    op.drop_column('users', 'terms_accepted_at')
    op.drop_column('users', 'consent_updated_at')
    op.drop_column('users', 'consent_ai_training')
    op.drop_column('users', 'consent_third_party')
    op.drop_column('users', 'consent_analytics')
    op.drop_column('users', 'consent_marketing')
    op.drop_column('users', 'email_verification_expires')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'is_2fa_enabled')
    op.drop_column('users', 'backup_codes')
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'verified_at')
