"""add lead status for gatekeeper

Revision ID: 9b1f7c2d4a11
Revises: 5b6a2f3a12cd
Create Date: 2026-02-12 11:40:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b1f7c2d4a11'
down_revision = '5b6a2f3a12cd'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('lead', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=40), nullable=True))
        batch_op.create_index(batch_op.f('ix_lead_status'), ['status'], unique=False)
    op.execute("UPDATE lead SET status='prospect' WHERE status IS NULL")


def downgrade():
    with op.batch_alter_table('lead', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_lead_status'))
        batch_op.drop_column('status')

