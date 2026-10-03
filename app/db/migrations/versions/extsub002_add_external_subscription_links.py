"""add external subscription links cache table

Revision ID: extsub002
Revises: extsub001
Create Date: 2026-10-03 09:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "extsub002"
down_revision = "extsub001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "external_subscription_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("link", sa.String(length=2048), nullable=False),
        sa.Column("link_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["subscription_id"], ["external_subscriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_subscription_links_subscription_id",
        "external_subscription_links",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_external_subscription_links_link_hash",
        "external_subscription_links",
        ["link_hash"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_external_subscription_links_link_hash", table_name="external_subscription_links")
    op.drop_index("ix_external_subscription_links_subscription_id", table_name="external_subscription_links")
    op.drop_table("external_subscription_links")