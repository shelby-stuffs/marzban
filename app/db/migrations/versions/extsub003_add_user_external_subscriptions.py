"""add user-external subscription association

Revision ID: extsub003
Revises: extsub002
Create Date: 2026-10-03 09:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "extsub003"
down_revision = "extsub002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_external_subscriptions",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("external_subscription_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["external_subscription_id"], ["external_subscriptions.id"]),
        sa.PrimaryKeyConstraint("user_id", "external_subscription_id"),
    )


def downgrade():
    op.drop_table("user_external_subscriptions")