"""Tests for the database transfer helpers.

The copy runs between two SQLite files, so the tests need no server. What they
actually check is that the copy goes through SQLAlchemy's type layer: enums come
back as enum members, datetimes as datetimes and booleans as booleans, which is
the part that breaks when rows are moved with raw SQL.
"""

from datetime import datetime

import pytest
from sqlalchemy import insert, select

from app.db import transfer
from app.db.models import Admin, Node, NodeUsage, NodeUserUsage, User
from app.models.node import NodeStatus
from app.models.user import UserDataLimitResetStrategy, UserStatus

ADMIN_CREATED_AT = datetime(2026, 1, 2, 3, 4, 5)
USER_CREATED_AT = datetime(2026, 2, 3, 4, 5, 6)
USAGE_CREATED_AT = datetime(2026, 9, 5, 9, 0, 0)


def seed(engine):
    transfer.bootstrap_schema(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(Admin.__table__),
            [
                {
                    "id": 1,
                    "username": "root",
                    "hashed_password": "hashed",
                    "is_sudo": True,
                    "created_at": ADMIN_CREATED_AT,
                    "users_usage": 0,
                }
            ],
        )
        connection.execute(
            insert(User.__table__),
            [
                {
                    "id": 1,
                    "username": "Alice",
                    "status": UserStatus.active,
                    "used_traffic": 1024,
                    "data_limit": 2048,
                    "data_limit_reset_strategy": UserDataLimitResetStrategy.no_reset,
                    "admin_id": 1,
                    "created_at": USER_CREATED_AT,
                },
                {
                    "id": 2,
                    "username": "bob",
                    "status": UserStatus.limited,
                    "used_traffic": 512,
                    "data_limit_reset_strategy": UserDataLimitResetStrategy.no_reset,
                    "admin_id": 1,
                    "created_at": USER_CREATED_AT,
                },
            ],
        )
        connection.execute(
            insert(Node.__table__),
            [
                {
                    "id": 1,
                    "name": "de-1",
                    "address": "192.0.2.10",
                    "port": 62050,
                    "api_port": 62051,
                    "status": NodeStatus.connected,
                    "usage_coefficient": 1.0,
                    "created_at": ADMIN_CREATED_AT,
                    "uplink": 0,
                    "downlink": 0,
                }
            ],
        )
        connection.execute(
            insert(NodeUserUsage.__table__),
            [
                {"id": 1, "created_at": USAGE_CREATED_AT, "user_id": 1, "node_id": 1, "used_traffic": 700},
                {"id": 2, "created_at": USAGE_CREATED_AT, "user_id": 2, "node_id": 1, "used_traffic": 300},
            ],
        )
        connection.execute(
            insert(NodeUsage.__table__),
            [{"id": 1, "created_at": USAGE_CREATED_AT, "node_id": 1, "uplink": 400, "downlink": 600}],
        )


@pytest.fixture
def engines(tmp_path):
    source = transfer.make_engine(f"sqlite:///{tmp_path / 'source.sqlite3'}")
    target = transfer.make_engine(f"sqlite:///{tmp_path / 'target.sqlite3'}")
    seed(source)
    transfer.bootstrap_schema(target)
    try:
        yield source, target
    finally:
        source.dispose()
        target.dispose()


def test_tables_are_sorted_parents_first():
    names = transfer.known_table_names()
    assert names.index("admins") < names.index("users")
    assert names.index("users") < names.index("node_user_usages")
    assert names.index("nodes") < names.index("node_user_usages")


def test_existing_tables_reports_the_schema(engines):
    source, _ = engines
    tables = transfer.existing_tables(source)
    assert "users" in tables
    assert "nodes" in tables


def test_copy_moves_every_row(engines):
    source, target = engines

    reports = {report.name: report for report in transfer.copy_database(source, target)}

    assert reports["admins"].copied_rows == 1
    assert reports["users"].copied_rows == 2
    assert reports["nodes"].copied_rows == 1
    assert reports["node_user_usages"].copied_rows == 2
    assert reports["node_usages"].copied_rows == 1
    assert all(report.ok for report in reports.values())


def test_copy_works_in_small_batches(engines):
    source, target = engines

    reports = {report.name: report for report in transfer.copy_database(source, target, batch_size=1)}

    assert reports["node_user_usages"].copied_rows == 2
    assert reports["users"].copied_rows == 2


def test_copy_preserves_value_types(engines):
    source, target = engines
    transfer.copy_database(source, target)

    with target.connect() as connection:
        admin = connection.execute(select(Admin.__table__)).mappings().one()
        user = connection.execute(
            select(User.__table__).where(User.__table__.c.id == 1)
        ).mappings().one()

    assert admin["is_sudo"] is True
    assert admin["created_at"] == ADMIN_CREATED_AT
    assert user["username"] == "Alice"
    assert user["status"] is UserStatus.active
    assert user["data_limit_reset_strategy"] is UserDataLimitResetStrategy.no_reset
    assert user["created_at"] == USER_CREATED_AT
    assert user["used_traffic"] == 1024


def test_verify_passes_after_a_full_copy(engines):
    source, target = engines
    transfer.copy_database(source, target)

    checks = {check.name: check for check in transfer.verify(source, target)}

    assert checks["users"].source == 2
    assert checks["sum(users.used_traffic)"].target == 1536
    assert checks["sum(node_user_usages.used_traffic)"].target == 1000
    assert checks["sum(node_usages.uplink)"].target == 400
    assert all(check.ok for check in checks.values())


def test_verify_notices_a_partial_copy(engines):
    source, target = engines
    transfer.copy_database(source, target, only=["admins", "nodes"])

    checks = {check.name: check for check in transfer.verify(source, target)}

    assert checks["admins"].ok
    assert not checks["users"].ok
    assert checks["users"].target == 0
    assert not checks["sum(users.used_traffic)"].ok


def test_sequence_reset_is_a_noop_outside_postgres(engines):
    _, target = engines
    assert transfer.reset_sequences(target) == {}


def test_version_table_roundtrip(engines):
    _, target = engines

    assert transfer.read_version(target) == []

    transfer.write_version(target, ["abc123def456"])
    assert transfer.read_version(target) == ["abc123def456"]

    transfer.write_version(target, ["fedcba654321"])
    assert transfer.read_version(target) == ["fedcba654321"]


def test_script_heads_are_available():
    assert transfer.script_heads()


def test_normalizes_a_bare_postgres_url():
    assert transfer.backend_of("postgresql://user:pass@localhost/marzban") == "postgresql"
    assert "psycopg" in transfer.describe("postgresql://user:pass@localhost/marzban")
    assert "pass" not in transfer.describe("postgresql://user:pass@localhost/marzban")
