"""Offline checks for the TimescaleDB helpers.

These never touch a server: they assert the generated statements and, more
usefully, that the hypertable definitions still line up with the models. If
someone renames a usage column, these fail instead of the setup command failing
on a production database.
"""

import pytest
from sqlalchemy import UniqueConstraint, create_engine

from app.db import timescale
from app.db.base import Base


def table_of(name: str):
    return Base.metadata.tables[name]


def test_hypertable_columns_exist_in_the_models():
    for hypertable in timescale.HYPERTABLES:
        table = table_of(hypertable.name)
        columns = set(table.columns.keys())
        assert hypertable.time_column in columns
        assert set(hypertable.segment_by) <= columns
        assert set(hypertable.key_columns) <= columns


def test_new_primary_key_includes_the_partitioning_column():
    # Timescale rejects any unique index that leaves the time column out.
    for hypertable in timescale.HYPERTABLES:
        assert hypertable.time_column in hypertable.key_columns


def test_model_unique_constraints_include_the_partitioning_column():
    # The ON CONFLICT target in record_usages relies on these constraints, so
    # they have to survive the conversion untouched.
    for hypertable in timescale.HYPERTABLES:
        table = table_of(hypertable.name)
        constraints = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
        assert constraints
        for constraint in constraints:
            assert hypertable.time_column in {column.name for column in constraint.columns}


def test_aggregates_point_at_hypertables_and_real_columns():
    names = {hypertable.name for hypertable in timescale.HYPERTABLES}
    for aggregate in timescale.AGGREGATES:
        assert aggregate.source in names
        columns = set(table_of(aggregate.source).columns.keys())
        assert aggregate.time_column in columns
        assert set(aggregate.group_by) <= columns
        for _, expression in aggregate.measures:
            assert expression.startswith("sum(") and expression.endswith(")")
            assert expression[4:-1] in columns


def test_hypertable_statement_migrates_existing_rows():
    statement = timescale.hypertable_sql(timescale.HYPERTABLES[0], 7)
    assert "create_hypertable('node_user_usages', 'created_at'" in statement
    assert "INTERVAL '7 days'" in statement
    assert "migrate_data => TRUE" in statement
    assert "if_not_exists => TRUE" in statement


def test_primary_key_statement_lists_the_time_column_first():
    assert (
        timescale.primary_key_sql(timescale.HYPERTABLES[0])
        == "ALTER TABLE node_user_usages ADD PRIMARY KEY (created_at, id)"
    )


def test_compression_segments_by_the_lookup_columns():
    statement = timescale.compression_sql(timescale.HYPERTABLES[0])
    assert "timescaledb.compress_segmentby = 'user_id, node_id'" in statement
    assert "timescaledb.compress_orderby = 'created_at DESC'" in statement


def test_aggregate_statement_is_a_daily_bucket_created_empty():
    statement = timescale.aggregate_sql(timescale.AGGREGATES[0])
    assert "timescaledb.continuous" in statement
    assert "time_bucket(INTERVAL '1 day', created_at) AS bucket" in statement
    assert "sum(used_traffic) AS used_traffic" in statement
    assert "GROUP BY bucket, user_id, node_id" in statement
    assert statement.endswith("WITH NO DATA")


def test_policy_statements_are_idempotent():
    hypertable = timescale.HYPERTABLES[0]
    assert "if_not_exists => TRUE" in timescale.compression_policy_sql(hypertable, 30)
    assert "if_not_exists => TRUE" in timescale.retention_policy_sql(hypertable, 365)
    assert "if_not_exists => TRUE" in timescale.aggregate_policy_sql(timescale.AGGREGATES[0])


@pytest.mark.parametrize(
    "call",
    [
        lambda: timescale.hypertable_sql(timescale.HYPERTABLES[0], 0),
        lambda: timescale.compression_policy_sql(timescale.HYPERTABLES[0], 0),
        lambda: timescale.retention_policy_sql(timescale.HYPERTABLES[0], 0),
    ],
)
def test_intervals_must_be_positive(call):
    with pytest.raises(ValueError):
        call()


def test_everything_refuses_to_run_outside_postgres():
    engine = create_engine("sqlite://")
    try:
        with pytest.raises(RuntimeError):
            timescale.require_postgres(engine)
        with pytest.raises(RuntimeError):
            timescale.status(engine)
        with pytest.raises(RuntimeError):
            timescale.setup(engine, chunk_days=7, compress_after_days=30, retention_days=0)
    finally:
        engine.dispose()
