"""add hysteria2 proxy type

Revision ID: h2y5t3r1a0001
Revises: 2b231de97dc3
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h2y5t3r1a0001'
down_revision = '2b231de97dc3'
branch_labels = None
depends_on = None


enum_name = "proxytypes"
temp_enum_name = f"temp_{enum_name}"
old_values = ("VMess", "VLESS", "Trojan", "Shadowsocks")
new_values = (*old_values, "Hysteria2")
downgrade_from = ("Hysteria2",)
downgrade_to = "VLESS"

old_type = sa.Enum(*old_values, name=enum_name)
new_type = sa.Enum(*new_values, name=enum_name)
temp_type = sa.Enum(*new_values, name=temp_enum_name)

table_name = "proxies"
column_name = "type"
temp_table = sa.sql.table(
    table_name,
    sa.Column(column_name, new_type, nullable=False)
)


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite stores enums as VARCHAR with CHECK constraint
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name,
                existing_type=old_type,
                type_=new_type,
                existing_nullable=False,
            )
        return

    temp_type.create(bind, checkfirst=False)
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=old_type,
            type_=temp_type,
            existing_nullable=False,
            postgresql_using=f"{column_name}::text::{temp_enum_name}"
        )

    old_type.drop(bind, checkfirst=False)
    new_type.create(bind, checkfirst=False)

    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=temp_type,
            type_=new_type,
            existing_nullable=False,
            postgresql_using=f"{column_name}::text::{enum_name}"
        )

    temp_type.drop(bind, checkfirst=False)


def downgrade():
    bind = op.get_bind()
    update_query = (
        temp_table.update()
        .where(temp_table.c.type.in_(downgrade_from))
        .values(type=downgrade_to)
    )
    op.execute(update_query)

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                column_name,
                existing_type=new_type,
                type_=old_type,
                existing_nullable=False,
            )
        return

    temp_type.create(bind, checkfirst=False)
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=new_type,
            type_=temp_type,
            existing_nullable=False,
            postgresql_using=f"{column_name}::text::{temp_enum_name}"
        )

    new_type.drop(bind, checkfirst=False)
    old_type.create(bind, checkfirst=False)

    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=temp_type,
            type_=old_type,
            existing_nullable=False,
            postgresql_using=f"{column_name}::text::{enum_name}"
        )

    temp_type.drop(bind, checkfirst=False)