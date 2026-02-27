"""expand ClipJob for viral reels v2 fields

Revision ID: d1a2b3c4d5e6
Revises: c0d1e2f3a4b5
Create Date: 2026-02-14

"""

from alembic import op
import sqlalchemy as sa


revision = 'd1a2b3c4d5e6'
down_revision = 'c0d1e2f3a4b5'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite-friendly batch alter for adding columns.
    with op.batch_alter_table('clip_job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('channel_name', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('segments_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('narration_path', sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column('output_path', sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column('metadata_json', sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP'))
        )

        batch_op.create_index('idx_clip_job_channel_name', ['channel_name'], unique=False)
        batch_op.create_index('idx_clip_job_created_at', ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('clip_job', schema=None) as batch_op:
        batch_op.drop_index('idx_clip_job_created_at')
        batch_op.drop_index('idx_clip_job_channel_name')

        batch_op.drop_column('created_at')
        batch_op.drop_column('metadata_json')
        batch_op.drop_column('output_path')
        batch_op.drop_column('narration_path')
        batch_op.drop_column('segments_json')
        batch_op.drop_column('channel_name')

