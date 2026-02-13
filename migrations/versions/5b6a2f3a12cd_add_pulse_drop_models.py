"""add pulse drop models

Revision ID: 5b6a2f3a12cd
Revises: 98e7cf4ac420
Create Date: 2026-02-12 11:05:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b6a2f3a12cd'
down_revision = '98e7cf4ac420'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'partner_video',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_name', sa.String(length=200), nullable=True),
        sa.Column('channel_id', sa.String(length=80), nullable=True),
        sa.Column('video_id', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail', sa.String(length=1000), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('harvested_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_id'),
    )
    with op.batch_alter_table('partner_video', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_partner_video_channel_id'), ['channel_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_partner_video_channel_name'), ['channel_name'], unique=False)
        batch_op.create_index(batch_op.f('ix_partner_video_harvested_at'), ['harvested_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_partner_video_published_at'), ['published_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_partner_video_video_id'), ['video_id'], unique=False)

    op.create_table(
        'pulse_segment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('partner_video_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.String(length=30), nullable=False),
        sa.Column('start_sec', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=300), nullable=True),
        sa.Column('priority', sa.Float(), nullable=True),
        sa.Column('intelligence_brief', sa.Text(), nullable=True),
        sa.Column('commentary_audio', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['partner_video_id'], ['partner_video.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('pulse_segment', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pulse_segment_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_pulse_segment_partner_video_id'), ['partner_video_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_pulse_segment_priority'), ['priority'], unique=False)
        batch_op.create_index(batch_op.f('ix_pulse_segment_video_id'), ['video_id'], unique=False)


def downgrade():
    with op.batch_alter_table('pulse_segment', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pulse_segment_video_id'))
        batch_op.drop_index(batch_op.f('ix_pulse_segment_priority'))
        batch_op.drop_index(batch_op.f('ix_pulse_segment_partner_video_id'))
        batch_op.drop_index(batch_op.f('ix_pulse_segment_created_at'))
    op.drop_table('pulse_segment')

    with op.batch_alter_table('partner_video', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_partner_video_video_id'))
        batch_op.drop_index(batch_op.f('ix_partner_video_published_at'))
        batch_op.drop_index(batch_op.f('ix_partner_video_harvested_at'))
        batch_op.drop_index(batch_op.f('ix_partner_video_channel_name'))
        batch_op.drop_index(batch_op.f('ix_partner_video_channel_id'))
    op.drop_table('partner_video')

