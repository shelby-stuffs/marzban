"""add per-host xhttp subscription settings

Revision ID: xhttphost001
Revises: wgpersist001
Create Date: 2026-09-04 07:38:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "xhttphost001"
down_revision = "wgpersist001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.add_column(sa.Column("xhttp_settings", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("hosts") as batch_op:
        batch_op.drop_column("xhttp_settings")
