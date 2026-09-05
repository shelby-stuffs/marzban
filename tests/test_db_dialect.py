"""Tests for the dialect helpers backing multi-database support.

These run entirely offline: statements are compiled against the SQLAlchemy
dialects without opening a connection.
"""

from sqlalchemy import BigInteger, Column, DateTime, Integer, MetaData, Table
from sqlalchemy.dialects import mysql, postgresql, sqlite

from app.db.dialect import (
    MYSQL_DEADLOCK,
    MYSQL_LOCK_WAIT_TIMEOUT,
    dialect_name,
    insert_ignore,
    is_mysql,
    is_postgres,
    is_retryable_error,
    is_sqlite,
)

metadata = MetaData()

usages = Table(
    "usages",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("created_at", DateTime, nullable=False),
    Column("node_id", Integer),
    Column("used_traffic", BigInteger),
)

VALUES = {"created_at": None, "node_id": 1, "used_traffic": 0}


class FakeBind:
    def __init__(self, name):
        self.name = name


class FakeSession:
    def __init__(self, name):
        self.bind = FakeBind(name)


class FakeDialect:
    def __init__(self, name):
        self.name = name


class FakeConnection:
    def __init__(self, name):
        self.dialect = FakeDialect(name)


class FakeWrapper(Exception):
    """Stands in for sqlalchemy.exc.DBAPIError, which wraps the driver error."""

    def __init__(self, orig):
        super().__init__(str(orig))
        self.orig = orig


class FakePgError(Exception):
    def __init__(self, sqlstate):
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def test_dialect_name_reads_session_engine_and_connection():
    assert dialect_name(FakeSession("postgresql")) == "postgresql"
    assert dialect_name(FakeBind("mysql")) == "mysql"
    assert dialect_name(FakeConnection("sqlite")) == "sqlite"
    assert dialect_name(object()) == ""


def test_dialect_predicates():
    assert is_sqlite(FakeSession("sqlite"))
    assert is_mysql(FakeSession("mysql"))
    assert is_postgres(FakeSession("postgresql"))
    assert not is_postgres(FakeSession("sqlite"))


def test_insert_ignore_uses_on_conflict_on_postgres():
    stmt = insert_ignore(FakeSession("postgresql"), usages, VALUES)
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT DO NOTHING" in sql


def test_insert_ignore_uses_insert_ignore_on_mysql():
    stmt = insert_ignore(FakeSession("mysql"), usages, VALUES)
    sql = str(stmt.compile(dialect=mysql.dialect()))
    assert sql.strip().startswith("INSERT IGNORE INTO")


def test_insert_ignore_stays_plain_on_sqlite():
    stmt = insert_ignore(FakeSession("sqlite"), usages, VALUES)
    sql = str(stmt.compile(dialect=sqlite.dialect()))
    assert sql.strip().startswith("INSERT INTO")
    assert "ON CONFLICT" not in sql


def test_mysql_retries_only_transient_errors():
    session = FakeSession("mysql")
    assert is_retryable_error(FakeWrapper(Exception(MYSQL_DEADLOCK, "deadlock")), session)
    assert is_retryable_error(FakeWrapper(Exception(MYSQL_LOCK_WAIT_TIMEOUT, "timeout")), session)
    assert not is_retryable_error(FakeWrapper(Exception(1064, "syntax error")), session)


def test_postgres_retries_only_serialization_failures():
    session = FakeSession("postgresql")
    assert is_retryable_error(FakeWrapper(FakePgError("40P01")), session)
    assert is_retryable_error(FakeWrapper(FakePgError("40001")), session)
    assert not is_retryable_error(FakeWrapper(FakePgError("23505")), session)


def test_sqlite_never_retries():
    session = FakeSession("sqlite")
    assert not is_retryable_error(FakeWrapper(Exception(MYSQL_DEADLOCK, "deadlock")), session)
