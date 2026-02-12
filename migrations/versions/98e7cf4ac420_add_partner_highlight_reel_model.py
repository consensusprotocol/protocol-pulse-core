"""add partner_highlight_reel model

Revision ID: 98e7cf4ac420
Revises: 4638db2794ee
Create Date: 2026-02-12 10:25:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '98e7cf4ac420'
down_revision = '4638db2794ee'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'partner_highlight_reel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('theme', sa.String(length=200), nullable=True),
        sa.Column('story_json', sa.Text(), nullable=True),
        sa.Column('video_path', sa.String(length=500), nullable=True),
        sa.Column('audio_path', sa.String(length=500), nullable=True),
        sa.Column('clips_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('source_summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('partner_highlight_reel', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_partner_highlight_reel_date'), ['date'], unique=False)


def downgrade():
    with op.batch_alter_table('partner_highlight_reel', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_partner_highlight_reel_date'))
    op.drop_table('partner_highlight_reel')

