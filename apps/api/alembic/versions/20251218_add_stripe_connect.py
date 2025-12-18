"""Add stripe_connect_account_id to users

Revision ID: 20251218_stripe_connect
Revises: 20251218_notifications
Create Date: 2025-12-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251218_stripe_connect'
down_revision: Union[str, None] = '20251218_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add stripe_connect_account_id column for creator payouts
    op.add_column(
        'users',
        sa.Column('stripe_connect_account_id', sa.String(255), nullable=True)
    )

    # Add index for faster lookups
    op.create_index(
        'idx_users_stripe_connect',
        'users',
        ['stripe_connect_account_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('idx_users_stripe_connect', table_name='users')
    op.drop_column('users', 'stripe_connect_account_id')
