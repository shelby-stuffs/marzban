"""Copy a Marzban database from one backend to another.

The historical alembic chain cannot be replayed on PostgreSQL: several
revisions branch on ``mysql``/``sqlite`` only and a few of them use
``sqlalchemy.dialects.mysql.VARCHAR`` directly. The target schema is therefore
created from the current models and the version table is written by hand, which
is exactly what ``alembic stamp`` does.

Rows are read and written through the model metadata rather than raw SQL, so
SQLAlchemy's type processors take care of the backend differences: SQLite keeps
timestamps as text and booleans as integers, while PostgreSQL expects real
``timestamp`` and ``boolean`` values, and enum columns are stored as native
enums with the member names as labels.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from sqlalchemy import (
    create_engine,
    func,
    insert,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.schema import Table

from app.db import models
from app.db.base import Base, normalize_url, render_url

logger = logging.getLogger(__name__)

VERSION_TABLE = "alembic_version"

# Sanity checks that go beyond row counts: a truncated or mistyped copy shows up
# as a different total.
CHECKSUMS = (
    ("sum(users.used_traffic)", models.User.__table__.c.used_traffic),
    ("sum(node_user_usages.used_traffic)", models.NodeUserUsage.__table__.c.used_traffic),
    ("sum(node_usages.uplink)", models.NodeUsage.__table__.c.uplink),
    ("sum(node_usages.downlink)", models.NodeUsage.__table__.c.downlink),
)


@dataclass
class TableReport:
    """How many rows a single table contributed."""

    name: str
    source_rows: int
    copied_rows: int

    @property
    def ok(self) -> bool:
        return self.source_rows == self.copied_rows


@dataclass
class CheckResult:
    """One line of the post-copy comparison."""

    name: str
    source: int
    target: int

    @property
    def ok(self) -> bool:
        return self.source == self.target


def make_engine(url: str) -> Engine:
    """Build a short-lived engine for a URL given on the command line."""

    normalized, backend = normalize_url(url)
    if backend == "sqlite":
        return create_engine(normalized, connect_args={"check_same_thread": False})
    return create_engine(normalized, pool_pre_ping=True)


def describe(url: str) -> str:
    normalized, backend = normalize_url(url)
    return f"{backend}: {render_url(normalized)}"


def backend_of(url: str) -> str:
    return normalize_url(url)[1]


def sorted_tables() -> List[Table]:
    """Model tables in dependency order, parents first."""

    return list(Base.metadata.sorted_tables)


def known_table_names() -> List[str]:
    return [table.name for table in sorted_tables()]


def existing_tables(engine: Engine) -> List[str]:
    """Model tables that already exist in the given database."""

    present = set(inspect(engine).get_table_names())
    return [name for name in known_table_names() if name in present]


def bootstrap_schema(engine: Engine) -> None:
    """Create every missing table, index and constraint from the models."""

    Base.metadata.create_all(engine)


def script_heads(config_path: str = "alembic.ini") -> List[str]:
    """Head revisions of the migration scripts on disk.

    ``alembic stamp`` is not used because ``app/db/migrations/env.py`` overrides
    the URL with the configured one, which would stamp the wrong database.
    """

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(Config(config_path))
    return list(script.get_heads())


def read_version(engine: Engine) -> List[str]:
    """Revisions recorded in the target's alembic version table."""

    if not inspect(engine).has_table(VERSION_TABLE):
        return []
    with engine.connect() as connection:
        rows = connection.execute(text(f"SELECT version_num FROM {VERSION_TABLE}"))
        return [row[0] for row in rows]


def write_version(engine: Engine, revisions: Sequence[str]) -> None:
    """Replace the alembic version table contents, like ``alembic stamp``."""

    with engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {VERSION_TABLE} ("
                "version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            )
        )
        connection.execute(text(f"DELETE FROM {VERSION_TABLE}"))
        for revision in revisions:
            connection.execute(
                text(f"INSERT INTO {VERSION_TABLE} (version_num) VALUES (:revision)"),
                {"revision": revision},
            )


def count_rows(connection, table: Table) -> int:
    return int(connection.execute(select(func.count()).select_from(table)).scalar_one())


def sum_column(connection, column) -> int:
    return int(connection.execute(select(func.coalesce(func.sum(column), 0))).scalar_one())


def copy_table(source_connection, target_connection, table: Table, batch_size: int) -> TableReport:
    total = count_rows(source_connection, table)
    if not total:
        return TableReport(table.name, 0, 0)

    copied = 0
    result = source_connection.execution_options(
        stream_results=True, yield_per=batch_size
    ).execute(select(table))
    for partition in result.partitions(batch_size):
        rows = [dict(row._mapping) for row in partition]
        target_connection.execute(insert(table), rows)
        copied += len(rows)

    return TableReport(table.name, total, copied)


def copy_database(
    source_engine: Engine,
    target_engine: Engine,
    batch_size: int = 1000,
    only: Optional[Sequence[str]] = None,
) -> List[TableReport]:
    """Copy every model table in dependency order.

    The whole copy runs in a single transaction on the target, so a failure
    halfway through leaves no partial data behind.
    """

    wanted = set(only) if only else None
    reports: List[TableReport] = []
    with source_engine.connect() as source_connection:
        with target_engine.begin() as target_connection:
            for table in sorted_tables():
                if wanted is not None and table.name not in wanted:
                    continue
                report = copy_table(source_connection, target_connection, table, batch_size)
                logger.info("copied %s rows into %s", report.copied_rows, table.name)
                reports.append(report)
    return reports


def reset_sequences(engine: Engine) -> Dict[str, int]:
    """Move PostgreSQL identity sequences past the copied ids.

    Explicit ids do not advance a sequence, so without this the first insert
    after the migration collides with an existing primary key. No-op elsewhere.
    """

    if engine.dialect.name != "postgresql":
        return {}

    updated: Dict[str, int] = {}
    with engine.begin() as connection:
        for table in sorted_tables():
            for column in table.primary_key.columns:
                try:
                    if column.type.python_type is not int:
                        continue
                except NotImplementedError:  # pragma: no cover - exotic column type
                    continue

                sequence = connection.execute(
                    text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
                    {"table_name": table.name, "column_name": column.name},
                ).scalar()
                if not sequence:
                    continue

                maximum = connection.execute(select(func.max(column))).scalar()
                if maximum is None:
                    connection.execute(
                        text("SELECT setval(:sequence, 1, false)"), {"sequence": sequence}
                    )
                    updated[f"{table.name}.{column.name}"] = 0
                else:
                    connection.execute(
                        text("SELECT setval(:sequence, :value, true)"),
                        {"sequence": sequence, "value": int(maximum)},
                    )
                    updated[f"{table.name}.{column.name}"] = int(maximum)
    return updated


def verify(source_engine: Engine, target_engine: Engine) -> List[CheckResult]:
    """Compare row counts and traffic totals on both sides."""

    checks: List[CheckResult] = []
    with source_engine.connect() as source_connection:
        with target_engine.connect() as target_connection:
            for table in sorted_tables():
                checks.append(
                    CheckResult(
                        table.name,
                        count_rows(source_connection, table),
                        count_rows(target_connection, table),
                    )
                )
            for label, column in CHECKSUMS:
                checks.append(
                    CheckResult(
                        label,
                        sum_column(source_connection, column),
                        sum_column(target_connection, column),
                    )
                )
    return checks
