"""Add creator earnings table for payout tracking

Revision ID: 20251222_earnings
Revises: 20251221_data_integrity_constraints
Create Date: 2024-12-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = '20251222_earnings'
down_revision = '20251221_data_integrity'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create earning status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE earningstatus AS ENUM ('PENDING', 'AVAILABLE', 'PAID', 'REFUNDED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create creator_earnings table
    op.create_table(
        'creator_earnings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('creator_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), index=True),
        sa.Column('license_id', UUID(as_uuid=True), sa.ForeignKey('licenses.id', ondelete='SET NULL'), index=True),
        sa.Column('identity_id', UUID(as_uuid=True), sa.ForeignKey('identities.id', ondelete='SET NULL'), index=True),

        # Amounts
        sa.Column('gross_amount', sa.Float, nullable=False),
        sa.Column('platform_fee', sa.Float, nullable=False),
        sa.Column('net_amount', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3), default='USD'),

        # Status
        sa.Column('status', sa.Enum('PENDING', 'AVAILABLE', 'PAID', 'REFUNDED', name='earningstatus'), default='PENDING', index=True),

        # Timing
        sa.Column('earned_at', sa.DateTime, default=sa.func.now()),
        sa.Column('available_at', sa.DateTime),
        sa.Column('paid_at', sa.DateTime),

        # Payout tracking
        sa.Column('payout_id', UUID(as_uuid=True), sa.ForeignKey('payouts.id', ondelete='SET NULL'), index=True),

        # Refund tracking
        sa.Column('refunded_at', sa.DateTime),
        sa.Column('refund_reason', sa.String(500)),

        # Metadata
        sa.Column('description', sa.String(500)),
        sa.Column('extra_data', JSONB, default=dict),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Add constraints
    op.execute("""
        ALTER TABLE creator_earnings
        ADD CONSTRAINT chk_earning_gross_positive
        CHECK (gross_amount > 0);
    """)

    op.execute("""
        ALTER TABLE creator_earnings
        ADD CONSTRAINT chk_earning_fee_positive
        CHECK (platform_fee >= 0);
    """)

    op.execute("""
        ALTER TABLE creator_earnings
        ADD CONSTRAINT chk_earning_net_positive
        CHECK (net_amount > 0);
    """)

    op.execute("""
        ALTER TABLE creator_earnings
        ADD CONSTRAINT chk_earning_net_not_exceed_gross
        CHECK (net_amount <= gross_amount);
    """)

    op.execute("""
        ALTER TABLE creator_earnings
        ADD CONSTRAINT chk_earning_available_after_earned
        CHECK (available_at IS NULL OR available_at >= earned_at);
    """)

    op.execute("""
        ALTER TABLE creator_earnings
        ADD CONSTRAINT chk_earning_paid_after_available
        CHECK (paid_at IS NULL OR paid_at >= available_at);
    """)

    # Create indexes for common queries
    op.create_index(
        'idx_earning_creator_status',
        'creator_earnings',
        ['creator_id', 'status']
    )

    op.create_index(
        'idx_earning_available',
        'creator_earnings',
        ['creator_id', 'status', 'available_at']
    )

    op.create_index(
        'idx_earning_payout',
        'creator_earnings',
        ['payout_id']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_earning_payout', table_name='creator_earnings')
    op.drop_index('idx_earning_available', table_name='creator_earnings')
    op.drop_index('idx_earning_creator_status', table_name='creator_earnings')

    # Drop table
    op.drop_table('creator_earnings')

    # Drop enum (optional - keep if other things use it)
    op.execute("DROP TYPE IF EXISTS earningstatus;")
