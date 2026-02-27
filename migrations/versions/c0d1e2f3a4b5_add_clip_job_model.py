"""add ClipJob model

Revision ID: c0d1e2f3a4b5
Revises: a1b2c3d4e5f6
Create Date: 2026-02-14

"""

from alembic import op
import sqlalchemy as sa


revision = 'c0d1e2f3a4b5'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'clip_job',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.String(length=100), nullable=False),
        sa.Column('timestamps_json', sa.Text(), nullable=False),
        sa.Column('narrative_context', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('clip_job', schema=None) as batch_op:
        batch_op.create_index('idx_clip_job_video_id', ['video_id'], unique=False)
        batch_op.create_index('idx_clip_job_status', ['status'], unique=False)


def downgrade():
    with op.batch_alter_table('clip_job', schema=None) as batch_op:
        batch_op.drop_index('idx_clip_job_status')
        batch_op.drop_index('idx_clip_job_video_id')
    op.drop_table('clip_job')

