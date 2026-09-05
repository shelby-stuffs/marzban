"""Optional TimescaleDB support for the usage tables.

The panel runs perfectly well on plain PostgreSQL. Everything in this module is
opt-in and applied explicitly through ``marzban-cli db timescale-setup``; no
query in the application changes, because hypertables and continuous aggregates
are transparent to SQLAlchemy.

Three constraints shaped the design:

* A hypertable cannot carry a unique index that does not include the
  partitioning column, so the plain ``id`` primary key of the usage tables has
  to become ``(created_at, id)``. ``id`` keeps its sequence default and stays
  unique in practice, which is all the ORM identity map needs.
* The ``UniqueConstraint('created_at', ...)`` already declared on both usage
  tables does include the partitioning column, so the ``INSERT ... ON CONFLICT
  DO NOTHING`` path in ``app/jobs/record_usages.py`` keeps working untouched.
* ``CREATE MATERIALIZED VIEW ... WITH (timescaledb.continuous)`` and
  ``refresh_continuous_aggregate()`` cannot run inside a transaction block, so
  the setup path uses an AUTOCOMMIT connection instead of the usual one.

Only ``node_user_usages`` and ``node_usages`` are converted. ``user_usage_logs``
is deliberately left alone: its time column is nullable and it gains one row per
traffic reset, so partitioning it would buy nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

POSTGRESQL = "postgresql"
EXTENSION = "timescaledb"
BUCKET = "1 day"


@dataclass(frozen=True)
class Hypertable:
    """A table to be partitioned by time."""

    name: str
    time_column: str
    segment_by: tuple[str, ...]
    key_columns: tuple[str, ...]


@dataclass(frozen=True)
class Aggregate:
    """A continuous aggregate rolling a hypertable up into daily buckets."""

    name: str
    source: str
    time_column: str
    group_by: tuple[str, ...]
    measures: tuple[tuple[str, str], ...]
    start_offset_days: int = 7


HYPERTABLES: tuple[Hypertable, ...] = (
    Hypertable(
        name="node_user_usages",
        time_column="created_at",
        segment_by=("user_id", "node_id"),
        key_columns=("created_at", "id"),
    ),
    Hypertable(
        name="node_usages",
        time_column="created_at",
        segment_by=("node_id",),
        key_columns=("created_at", "id"),
    ),
)

AGGREGATES: tuple[Aggregate, ...] = (
    Aggregate(
        name="node_user_usages_daily",
        source="node_user_usages",
        time_column="created_at",
        group_by=("user_id", "node_id"),
        measures=(("used_traffic", "sum(used_traffic)"),),
    ),
    Aggregate(
        name="node_usages_daily",
        source="node_usages",
        time_column="created_at",
        group_by=("node_id",),
        measures=(("uplink", "sum(uplink)"), ("downlink", "sum(downlink)")),
    ),
)


# -- statement builders ------------------------------------------------------
#
# Kept pure so they can be asserted on without a live PostgreSQL server. Every
# identifier below comes from the constants above, never from user input.


def not_null_sql(table: Hypertable) -> str:
    return f"ALTER TABLE {table.name} ALTER COLUMN {table.time_column} SET NOT NULL"


def drop_primary_key_sql(table: str, constraint: str) -> str:
    return f'ALTER TABLE {table} DROP CONSTRAINT "{constraint}"'


def primary_key_sql(table: Hypertable) -> str:
    return f"ALTER TABLE {table.name} ADD PRIMARY KEY ({', '.join(table.key_columns)})"


def hypertable_sql(table: Hypertable, chunk_days: int) -> str:
    if chunk_days < 1:
        raise ValueError("chunk_days must be at least 1")
    return (
        f"SELECT create_hypertable('{table.name}', '{table.time_column}', "
        f"chunk_time_interval => INTERVAL '{chunk_days} days', "
        "migrate_data => TRUE, if_not_exists => TRUE)"
    )


def compression_sql(table: Hypertable) -> str:
    return (
        f"ALTER TABLE {table.name} SET ("
        "timescaledb.compress, "
        f"timescaledb.compress_segmentby = '{', '.join(table.segment_by)}', "
        f"timescaledb.compress_orderby = '{table.time_column} DESC')"
    )


def compression_policy_sql(table: Hypertable, after_days: int) -> str:
    if after_days < 1:
        raise ValueError("after_days must be at least 1")
    return (
        f"SELECT add_compression_policy('{table.name}', "
        f"INTERVAL '{after_days} days', if_not_exists => TRUE)"
    )


def retention_policy_sql(table: Hypertable, days: int) -> str:
    if days < 1:
        raise ValueError("days must be at least 1; use 0 to keep every row forever")
    return (
        f"SELECT add_retention_policy('{table.name}', "
        f"INTERVAL '{days} days', if_not_exists => TRUE)"
    )


def aggregate_sql(aggregate: Aggregate, bucket: str = BUCKET) -> str:
    measures = ", ".join(f"{expression} AS {name}" for name, expression in aggregate.measures)
    columns = ", ".join(aggregate.group_by)
    group_by = ", ".join(("bucket",) + aggregate.group_by)
    return (
        f"CREATE MATERIALIZED VIEW IF NOT EXISTS {aggregate.name} "
        "WITH (timescaledb.continuous) AS SELECT "
        f"time_bucket(INTERVAL '{bucket}', {aggregate.time_column}) AS bucket, "
        f"{columns}, {measures} "
        f"FROM {aggregate.source} "
        f"GROUP BY {group_by} "
        "WITH NO DATA"
    )


def aggregate_policy_sql(aggregate: Aggregate) -> str:
    return (
        f"SELECT add_continuous_aggregate_policy('{aggregate.name}', "
        f"start_offset => INTERVAL '{aggregate.start_offset_days} days', "
        "end_offset => INTERVAL '1 hour', "
        "schedule_interval => INTERVAL '1 hour', if_not_exists => TRUE)"
    )


def refresh_sql(aggregate: Aggregate) -> str:
    return f"CALL refresh_continuous_aggregate('{aggregate.name}', NULL, NULL)"


# -- inspection --------------------------------------------------------------

_EXTENSION_AVAILABLE = text("SELECT 1 FROM pg_available_extensions WHERE name = :name")
_EXTENSION_VERSION = text("SELECT extversion FROM pg_extension WHERE extname = :name")
_HYPERTABLE_INFO = text(
    "SELECT num_chunks, compression_enabled FROM timescaledb_information.hypertables "
    "WHERE hypertable_name = :name"
)
_AGGREGATE_EXISTS = text(
    "SELECT 1 FROM timescaledb_information.continuous_aggregates WHERE view_name = :name"
)
_JOBS = text(
    "SELECT proc_name FROM timescaledb_information.jobs WHERE hypertable_name = :name"
)
_PRIMARY_KEY_NAME = text(
    "SELECT conname FROM pg_constraint WHERE conrelid = :table::regclass AND contype = 'p'"
)
_PRIMARY_KEY_COLUMNS = text(
    "SELECT a.attname FROM pg_index i "
    "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
    "WHERE i.indrelid = :table::regclass AND i.indisprimary"
)


def require_postgres(bind: Any) -> None:
    """Refuses to touch anything but PostgreSQL."""

    name = bind.dialect.name
    if name != POSTGRESQL:
        raise RuntimeError(
            f"TimescaleDB is only available on PostgreSQL, the current backend is {name}. "
            "Migrate with 'marzban-cli db migrate' first."
        )


def autocommit(engine: Any) -> Any:
    """A connection that runs each statement on its own.

    Continuous aggregates cannot be created or refreshed inside a transaction
    block, which is what the default connection would give us.
    """

    return engine.connect().execution_options(isolation_level="AUTOCOMMIT")


def extension_available(connection: Any) -> bool:
    return connection.execute(_EXTENSION_AVAILABLE, {"name": EXTENSION}).first() is not None


def extension_version(connection: Any) -> str | None:
    row = connection.execute(_EXTENSION_VERSION, {"name": EXTENSION}).first()
    return row[0] if row else None


def install_extension(connection: Any) -> None:
    connection.execute(text(f"CREATE EXTENSION IF NOT EXISTS {EXTENSION} CASCADE"))


def is_hypertable(connection: Any, name: str) -> bool:
    return connection.execute(_HYPERTABLE_INFO, {"name": name}).first() is not None


def has_aggregate(connection: Any, name: str) -> bool:
    return connection.execute(_AGGREGATE_EXISTS, {"name": name}).first() is not None


def jobs(connection: Any, name: str) -> list[str]:
    return [row[0] for row in connection.execute(_JOBS, {"name": name})]


def primary_key_name(connection: Any, table: str) -> str | None:
    row = connection.execute(_PRIMARY_KEY_NAME, {"table": table}).first()
    return row[0] if row else None


def primary_key_columns(connection: Any, table: str) -> list[str]:
    return [row[0] for row in connection.execute(_PRIMARY_KEY_COLUMNS, {"table": table})]


# -- operations --------------------------------------------------------------


def status(engine: Any) -> dict:
    """Reports what has already been applied on the configured database."""

    require_postgres(engine)

    with engine.connect() as connection:
        report: dict = {
            "available": extension_available(connection),
            "extension": extension_version(connection),
            "hypertables": [],
            "aggregates": [],
        }

        if not report["extension"]:
            return report

        for table in HYPERTABLES:
            row = connection.execute(_HYPERTABLE_INFO, {"name": table.name}).first()
            report["hypertables"].append(
                {
                    "name": table.name,
                    "converted": row is not None,
                    "chunks": row[0] if row else 0,
                    "compressed": bool(row[1]) if row else False,
                    "jobs": jobs(connection, table.name),
                }
            )

        for aggregate in AGGREGATES:
            report["aggregates"].append(
                {"name": aggregate.name, "created": has_aggregate(connection, aggregate.name)}
            )

    return report


def setup(
    engine: Any,
    *,
    chunk_days: int,
    compress_after_days: int,
    retention_days: int,
    aggregates: bool = True,
) -> list[str]:
    """Converts the usage tables and installs the policies.

    Safe to run repeatedly: every step is guarded by an existence check or by
    ``if_not_exists``. Returns a log of what was done, for the CLI to print.
    """

    require_postgres(engine)

    log: list[str] = []

    with autocommit(engine) as connection:
        if not extension_available(connection):
            raise RuntimeError(
                "The timescaledb extension is not available on this server. Use a "
                "timescale/timescaledb image or install the TimescaleDB packages."
            )

        install_extension(connection)
        log.append(f"timescaledb extension {extension_version(connection)}")

        for table in HYPERTABLES:
            if is_hypertable(connection, table.name):
                log.append(f"{table.name}: already a hypertable")
            else:
                # The partitioning column has to be NOT NULL, and no unique
                # index may exclude it, so the id-only primary key goes first.
                connection.execute(text(not_null_sql(table)))

                if table.time_column not in primary_key_columns(connection, table.name):
                    existing = primary_key_name(connection, table.name)
                    if existing:
                        connection.execute(text(drop_primary_key_sql(table.name, existing)))
                    connection.execute(text(primary_key_sql(table)))
                    log.append(
                        f"{table.name}: primary key is now ({', '.join(table.key_columns)})"
                    )

                connection.execute(text(hypertable_sql(table, chunk_days)))
                log.append(f"{table.name}: hypertable with {chunk_days} day chunks")

            if compress_after_days > 0:
                connection.execute(text(compression_sql(table)))
                connection.execute(text(compression_policy_sql(table, compress_after_days)))
                log.append(f"{table.name}: compression after {compress_after_days} days")

            if retention_days > 0:
                connection.execute(text(retention_policy_sql(table, retention_days)))
                log.append(f"{table.name}: raw rows dropped after {retention_days} days")

        if aggregates:
            for aggregate in AGGREGATES:
                if has_aggregate(connection, aggregate.name):
                    log.append(f"{aggregate.name}: already exists")
                    continue
                connection.execute(text(aggregate_sql(aggregate)))
                connection.execute(text(aggregate_policy_sql(aggregate)))
                connection.execute(text(refresh_sql(aggregate)))
                log.append(f"{aggregate.name}: continuous aggregate created and filled")

    return log
