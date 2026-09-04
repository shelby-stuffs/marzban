"""add wireguard server and peer storage

Revision ID: wgpersist001
Revises: 5d5f274f3971
Create Date: 2026-09-04 06:48:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "wgpersist001"
down_revision = "5d5f274f3971"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "wireguard_server",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("endpoint_address", sa.String(length=256), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "wireguard_peers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_wireguard_peers_user_id", "wireguard_peers", ["user_id"], unique=True)


def downgrade():
    op.drop_index("ix_wireguard_peers_user_id", table_name="wireguard_peers")
    op.drop_table("wireguard_peers")
    op.drop_table("wireguard_server")
