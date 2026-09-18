"""store per-user custom sing-box inbound selection

Revision ID: singboxusr001
Revises: themecomb001
Create Date: 2026-09-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "singboxusr001"
down_revision = "themecomb001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("singbox_inbounds", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("users", "singbox_inbounds")