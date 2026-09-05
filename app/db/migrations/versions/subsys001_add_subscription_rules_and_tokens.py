"""add subscription client rules and per-device tokens

Revision ID: subsys001
Revises: xhttphost001
Create Date: 2026-09-05 06:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "subsys001"
down_revision = "xhttphost001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subscription_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("pattern", sa.String(length=512), nullable=False),
        sa.Column("config_format", sa.String(length=32), nullable=False),
        sa.Column("as_base64", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("reverse", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("ignore_case", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("min_version", sa.String(length=32), nullable=True),
        sa.Column("max_version", sa.String(length=32), nullable=True),
        sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "subscription_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("last_user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subscription_tokens_token", "subscription_tokens", ["token"], unique=True
    )
    op.create_index(
        "ix_subscription_tokens_user_id", "subscription_tokens", ["user_id"], unique=False
    )


def downgrade():
    op.drop_index("ix_subscription_tokens_user_id", table_name="subscription_tokens")
    op.drop_index("ix_subscription_tokens_token", table_name="subscription_tokens")
    op.drop_table("subscription_tokens")
    op.drop_table("subscription_rules")
