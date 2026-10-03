"""merge extsub and singboxusr heads

Revision ID: merge001
Revises: singboxusr001, extsub003
Create Date: 2026-10-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "merge001"
down_revision = ("singboxusr001", "extsub003")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass