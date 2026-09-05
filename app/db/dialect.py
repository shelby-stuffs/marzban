"""Dialect-specific helpers for the database layer.

Marzban historically supported SQLite and MySQL only, and the runtime code
branched on ``db.bind.name == "mysql"`` in a couple of places. PostgreSQL (and
therefore TimescaleDB, which is a PostgreSQL extension) needs different
constructs for the very same intent, so all of those differences live here
instead of being spread across the codebase.

This module deliberately imports nothing from ``app``, so it stays cheap to
import and easy to test.
"""

from typing import Any, Mapping, Optional

from sqlalchemy import insert as sa_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql.dml import Insert

SQLITE = "sqlite"
MYSQL = "mysql"
POSTGRESQL = "postgresql"

# "Deadlock found when trying to get lock; try restarting transaction"
MYSQL_DEADLOCK = 1213
# "Lock wait timeout exceeded"
MYSQL_LOCK_WAIT_TIMEOUT = 1205
MYSQL_RETRY_CODES = frozenset({MYSQL_DEADLOCK, MYSQL_LOCK_WAIT_TIMEOUT})

# deadlock_detected and serialization_failure
POSTGRES_RETRY_SQLSTATES = frozenset({"40P01", "40001"})


def dialect_name(target: Any) -> str:
    """Return the backend name for a Session, Engine or Connection.

    Accepts anything that either exposes ``name`` itself (Engine, Connection)
    or holds such an object in ``bind`` (Session).
    """

    candidates = (getattr(target, "bind", None), target)
    for candidate in candidates:
        if candidate is None:
            continue
        name = getattr(candidate, "name", None)
        if isinstance(name, str) and name:
            return name
        dialect = getattr(candidate, "dialect", None)
        name = getattr(dialect, "name", None)
        if isinstance(name, str) and name:
            return name
    return ""


def is_sqlite(target: Any) -> bool:
    return dialect_name(target) == SQLITE


def is_mysql(target: Any) -> bool:
    return dialect_name(target) == MYSQL


def is_postgres(target: Any) -> bool:
    return dialect_name(target) == POSTGRESQL


def insert_ignore(target: Any, table: Any, values: Mapping[str, Any]) -> Insert:
    """Build an INSERT that silently skips rows violating a unique constraint.

    MySQL gets ``INSERT IGNORE``, PostgreSQL gets ``ON CONFLICT DO NOTHING``.
    SQLite keeps a plain INSERT: the callers pre-check for existing rows, and
    a plain statement is what this code has always emitted there.
    """

    name = dialect_name(target)
    if name == POSTGRESQL:
        return pg_insert(table).values(**values).on_conflict_do_nothing()
    if name == MYSQL:
        return sa_insert(table).values(**values).prefix_with("IGNORE")
    return sa_insert(table).values(**values)


def error_code(error: BaseException) -> Optional[int]:
    """Numeric driver error code, as used by MySQL."""

    args = getattr(error, "args", ())
    if args and isinstance(args[0], int):
        return args[0]
    return None


def sqlstate(error: BaseException) -> Optional[str]:
    """SQLSTATE of a driver error (psycopg 3 and psycopg2 name it differently)."""

    for attribute in ("sqlstate", "pgcode"):
        value = getattr(error, attribute, None)
        if value:
            return str(value)
    return None


def is_retryable_error(error: BaseException, target: Any) -> bool:
    """Whether a failed statement is worth retrying after a rollback.

    Only transient serialization problems qualify. Constraint violations and
    connection errors must surface instead of being retried in a loop.
    """

    original = getattr(error, "orig", None) or error
    name = dialect_name(target)

    if name == MYSQL:
        return error_code(original) in MYSQL_RETRY_CODES
    if name == POSTGRESQL:
        return sqlstate(original) in POSTGRES_RETRY_SQLSTATES
    return False
