"""V30: Add api_keys and api_usage_log tables for Pulse Terminal API.

Revision ID: a1b2c3d4e5f6
Revises: fb645588212d
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'a1b2c3d4e5f6'
down_revision = 'fb645588212d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('key_prefix', sa.String(length=12), nullable=False),
        sa.Column('tier', sa.String(length=30), nullable=False),
        sa.Column('subscriber_email', sa.String(length=200), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=120), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(length=120), nullable=True),
        sa.Column('stripe_session_id', sa.String(length=200), nullable=True),
        sa.Column('requests_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('requests_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('last_reset_at', sa.DateTime(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash'),
    )
    op.create_index('idx_api_keys_hash_active', 'api_keys', ['key_hash', 'active'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    op.create_index('ix_api_keys_subscriber_email', 'api_keys', ['subscriber_email'])
    op.create_index('ix_api_keys_stripe_customer_id', 'api_keys', ['stripe_customer_id'])
    op.create_index('ix_api_keys_last_used_at', 'api_keys', ['last_used_at'])
    op.create_index('ix_api_keys_active', 'api_keys', ['active'])

    op.create_table(
        'api_usage_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key_prefix', sa.String(length=12), nullable=False),
        sa.Column('endpoint', sa.String(length=100), nullable=False),
        sa.Column('response_ms', sa.Integer(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True, server_default='200'),
        sa.Column('ip_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_usage_log_key_prefix', 'api_usage_log', ['key_prefix'])
    op.create_index('ix_api_usage_log_created_at', 'api_usage_log', ['created_at'])
    op.create_index('idx_usage_log_prefix_created', 'api_usage_log',
                    ['key_prefix', 'created_at'])


def downgrade():
    op.drop_index('idx_usage_log_prefix_created', table_name='api_usage_log')
    op.drop_index('ix_api_usage_log_created_at', table_name='api_usage_log')
    op.drop_index('ix_api_usage_log_key_prefix', table_name='api_usage_log')
    op.drop_table('api_usage_log')

    op.drop_index('idx_api_keys_hash_active', table_name='api_keys')
    op.drop_index('ix_api_keys_active', table_name='api_keys')
    op.drop_index('ix_api_keys_last_used_at', table_name='api_keys')
    op.drop_index('ix_api_keys_stripe_customer_id', table_name='api_keys')
    op.drop_index('ix_api_keys_subscriber_email', table_name='api_keys')
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_table('api_keys')
