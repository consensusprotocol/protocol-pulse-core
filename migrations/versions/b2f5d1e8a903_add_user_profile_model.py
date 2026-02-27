"""add user profile model

Revision ID: b2f5d1e8a903
Revises: 9b1f7c2d4a11
Create Date: 2026-02-12 12:35:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2f5d1e8a903"
down_revision = "9b1f7c2d4a11"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_profile",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("profile_json", sa.Text(), nullable=True),
        sa.Column("behavior_json", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    with op.batch_alter_table("user_profile", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_user_profile_updated_at"), ["updated_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_user_profile_user_id"), ["user_id"], unique=False)


def downgrade():
    with op.batch_alter_table("user_profile", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_profile_user_id"))
        batch_op.drop_index(batch_op.f("ix_user_profile_updated_at"))
    op.drop_table("user_profile")

