"""add SentryJob model (Megaphone V1)

Revision ID: a1b2c3d4e5f6
Revises: b2f5d1e8a903
Create Date: 2026-02-12 Phase 6 Megaphone

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'b2f5d1e8a903'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sentry_job',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('sentry_job', schema=None) as batch_op:
        batch_op.create_index('idx_sentry_job_status', ['status'], unique=False)


def downgrade():
    with op.batch_alter_table('sentry_job', schema=None) as batch_op:
        batch_op.drop_index('idx_sentry_job_status')
    op.drop_table('sentry_job')
