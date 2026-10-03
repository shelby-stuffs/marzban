"""add external subscriptions

Revision ID: extsub001
Revises: xhttphost001
Create Date: 2026-10-03 08:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "extsub001"
down_revision = "xhttphost001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "external_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("update_interval", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade():
    op.drop_table("external_subscriptions")