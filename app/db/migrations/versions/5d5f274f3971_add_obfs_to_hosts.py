"""add obfs and obfs_password to hosts

Revision ID: 5d5f274f3971
Revises: h2y5t3r1a0001
Create Date: 2026-07-12 13:26:16.274387

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5d5f274f3971'
down_revision = 'h2y5t3r1a0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('hosts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('obfs', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('obfs_password', sa.String(length=256), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('hosts', schema=None) as batch_op:
        batch_op.drop_column('obfs_password')
        batch_op.drop_column('obfs')
