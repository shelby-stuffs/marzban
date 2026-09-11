"""add account-scoped dashboard preferences

Revision ID: themecomb001
Revises: subsys001
Create Date: 2026-09-11 13:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "themecomb001"
down_revision = "subsys001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "admin_preferences",
        sa.Column("username", sa.String(length=34), nullable=False),
        sa.Column("dashboard_theme", sa.String(length=32), nullable=False, server_default="glamour-pink"),
        sa.PrimaryKeyConstraint("username"),
    )

def downgrade():
    op.drop_table("admin_preferences")
