import typer
from rich.console import Console
from rich.table import Table

from app.db import timescale, transfer
from app.db.base import DATABASE_URI
from config import (
    TIMESCALE_CHUNK_INTERVAL_DAYS,
    TIMESCALE_COMPRESS_AFTER_DAYS,
    TIMESCALE_ENABLED,
    TIMESCALE_RETENTION_DAYS,
)

from . import utils

app = typer.Typer(no_args_is_help=True)
console = Console()


def _print_checks(checks) -> bool:
    table = Table("Check", "Source", "Target", "", title="Verification")
    for check in checks:
        if check.source == 0 and check.target == 0:
            continue
        table.add_row(
            check.name,
            str(check.source),
            str(check.target),
            "ok" if check.ok else "MISMATCH",
        )
    console.print(table)
    return all(check.ok for check in checks)


@app.command(name="status")
def status():
    """
    Shows which database the panel is configured to use.

    Prints the backend, the tables that exist and the recorded migration
    revision, so the state of a database can be checked before and after a
    migration.
    """
    console.print(f"[bold]Configured database:[/bold] {transfer.describe(DATABASE_URI)}")

    engine = transfer.make_engine(DATABASE_URI)
    try:
        tables = transfer.existing_tables(engine)
        revisions = transfer.read_version(engine)

        console.print(f"[bold]Tables:[/bold] {len(tables)} of {len(transfer.known_table_names())}")
        console.print(f"[bold]Alembic revision:[/bold] {', '.join(revisions) or '-'}")
        console.print(f"[bold]Script heads:[/bold] {', '.join(transfer.script_heads()) or '-'}")

        if tables:
            with engine.connect() as connection:
                rows = Table("Table", "Rows", title="Row counts")
                for table in transfer.sorted_tables():
                    if table.name not in tables:
                        continue
                    rows.add_row(table.name, str(transfer.count_rows(connection, table)))
                console.print(rows)
    finally:
        engine.dispose()


@app.command(name="migrate")
def migrate(
    target_url: str = typer.Option(
        ...,
        "--to",
        prompt="Target database URL",
        help="Target database URL, e.g. postgresql://marzban:secret@127.0.0.1:5432/marzban",
    ),
    source_url: str = typer.Option(
        None,
        "--from",
        help="Source database URL. Defaults to the database the panel is configured with.",
    ),
    batch_size: int = typer.Option(1000, "--batch-size", min=1, help="Rows per insert batch."),
    force: bool = typer.Option(
        False,
        "--force",
        is_flag=True,
        help="Copy even if the target already contains Marzban tables.",
    ),
    yes_to_all: bool = typer.Option(
        False, *utils.FLAGS["yes_to_all"], is_flag=True, help="Skips the confirmation prompt."
    ),
):
    """
    Copies the whole database to another backend, typically SQLite to PostgreSQL.

    Creates the schema on the target from the current models, marks it as being
    at the latest migration, copies every table in dependency order, fixes the
    PostgreSQL sequences and compares row counts and traffic totals on both
    sides.

    STOP THE PANEL FIRST. Rows written while the copy runs are not picked up.
    The source database is only read from and is left untouched, so it stays
    usable as a fallback: nothing is deleted and the panel keeps using it until
    SQLALCHEMY_DATABASE_URL is changed by hand.
    """
    source_url = source_url or DATABASE_URI

    if transfer.backend_of(source_url) == "sqlite" and transfer.backend_of(target_url) == "sqlite":
        utils.error("Both URLs point at SQLite. There is nothing to migrate.")

    console.print(f"[bold]Source:[/bold] {transfer.describe(source_url)}")
    console.print(f"[bold]Target:[/bold] {transfer.describe(target_url)}")

    source_engine = transfer.make_engine(source_url)
    target_engine = transfer.make_engine(target_url)

    try:
        try:
            source_tables = transfer.existing_tables(source_engine)
        except Exception as exc:
            utils.error(f"Could not read the source database: {exc}")
            return

        if not source_tables:
            utils.error("The source database has no Marzban tables.")

        try:
            target_tables = transfer.existing_tables(target_engine)
        except Exception as exc:
            utils.error(f"Could not connect to the target database: {exc}")
            return

        if target_tables and not force:
            utils.error(
                "The target database already contains Marzban tables "
                f"({', '.join(target_tables)}). Drop them, use an empty database, "
                "or pass --force to copy into it anyway."
            )

        source_revisions = transfer.read_version(source_engine)
        heads = transfer.script_heads()
        if source_revisions and heads and set(source_revisions) != set(heads):
            console.print(
                "[yellow]Warning:[/yellow] the source is at "
                f"{', '.join(source_revisions)} while the scripts are at {', '.join(heads)}. "
                "Start the panel once on the source database to apply the pending migrations, "
                "otherwise the copy will not match the schema being created."
            )

        if not yes_to_all:
            typer.confirm(
                "The panel must be stopped before continuing. Proceed?", abort=True
            )

        console.print("Creating the schema on the target...")
        try:
            transfer.bootstrap_schema(target_engine)
        except Exception as exc:
            utils.error(
                f"Could not create the schema: {exc}\n"
                "On PostgreSQL the citext extension is required. Run "
                '"CREATE EXTENSION IF NOT EXISTS citext;" as a superuser and try again.'
            )
            return

        revisions = source_revisions or heads
        transfer.write_version(target_engine, revisions)
        console.print(f"Stamped the target at {', '.join(revisions) or '-'}")

        console.print("Copying data...")
        reports = transfer.copy_database(source_engine, target_engine, batch_size=batch_size)
        copied = Table("Table", "Rows", title="Copied")
        for report in reports:
            if report.source_rows:
                copied.add_row(report.name, str(report.copied_rows))
        console.print(copied)

        sequences = transfer.reset_sequences(target_engine)
        if sequences:
            console.print(f"Reset {len(sequences)} sequences.")

        if not _print_checks(transfer.verify(source_engine, target_engine)):
            utils.error("The target does not match the source. Do not switch the panel over.")

        utils.success(
            "Migration finished. Set SQLALCHEMY_DATABASE_URL to the target URL and start the "
            "panel. Keep the old database around until everything looks right.",
            auto_exit=False,
        )
    finally:
        source_engine.dispose()
        target_engine.dispose()


@app.command(name="verify")
def verify(
    other_url: str = typer.Option(
        ...,
        "--against",
        prompt="Database URL to compare against",
        help="The other database URL to compare the configured one with.",
    ),
):
    """
    Compares the configured database with another one.

    Useful after a migration to confirm that both databases still hold the same
    rows and the same traffic totals.
    """
    source_engine = transfer.make_engine(DATABASE_URI)
    target_engine = transfer.make_engine(other_url)
    try:
        if not _print_checks(transfer.verify(source_engine, target_engine)):
            utils.error("The two databases differ.")
        utils.success("Both databases match.", auto_exit=False)
    finally:
        source_engine.dispose()
        target_engine.dispose()


@app.command(name="timescale-status")
def timescale_status():
    """
    Shows the TimescaleDB state of the configured database.

    Reports whether the extension is installed, which usage tables have been
    converted into hypertables, how many chunks they hold, and which background
    jobs (compression, retention, aggregate refresh) are registered.
    """
    engine = transfer.make_engine(DATABASE_URI)
    try:
        try:
            report = timescale.status(engine)
        except RuntimeError as exc:
            utils.error(str(exc))
            return

        console.print(f"[bold]Database:[/bold] {transfer.describe(DATABASE_URI)}")
        console.print(f"[bold]Extension available:[/bold] {'yes' if report['available'] else 'no'}")
        console.print(f"[bold]Extension installed:[/bold] {report['extension'] or '-'}")

        if not report["extension"]:
            console.print("Nothing has been applied yet. Run 'marzban-cli db timescale-setup'.")
            return

        tables = Table("Table", "Hypertable", "Chunks", "Compression", "Jobs", title="Usage tables")
        for item in report["hypertables"]:
            tables.add_row(
                item["name"],
                "yes" if item["converted"] else "no",
                str(item["chunks"]),
                "on" if item["compressed"] else "off",
                ", ".join(item["jobs"]) or "-",
            )
        console.print(tables)

        views = Table("Continuous aggregate", "", title="Aggregates")
        for item in report["aggregates"]:
            views.add_row(item["name"], "ok" if item["created"] else "missing")
        console.print(views)
    finally:
        engine.dispose()


@app.command(name="timescale-setup")
def timescale_setup(
    chunk_days: int = typer.Option(
        TIMESCALE_CHUNK_INTERVAL_DAYS,
        "--chunk-days",
        min=1,
        help="Time span covered by a single chunk.",
    ),
    compress_after_days: int = typer.Option(
        TIMESCALE_COMPRESS_AFTER_DAYS,
        "--compress-after",
        min=0,
        help="Compress chunks older than this. 0 disables compression.",
    ),
    retention_days: int = typer.Option(
        TIMESCALE_RETENTION_DAYS,
        "--retention-days",
        min=0,
        help="Drop raw usage rows older than this. 0 keeps them forever.",
    ),
    skip_aggregates: bool = typer.Option(
        False,
        "--skip-aggregates",
        is_flag=True,
        help="Do not create the daily continuous aggregates.",
    ),
    yes_to_all: bool = typer.Option(
        False, *utils.FLAGS["yes_to_all"], is_flag=True, help="Skips the confirmation prompt."
    ),
):
    """
    Turns the usage tables into TimescaleDB hypertables.

    Converts node_user_usages and node_usages, adds daily continuous aggregates
    for the usage charts, and registers the compression and retention policies.
    Existing rows are migrated in place, so this can be run on a database that
    already holds history.

    Requires PostgreSQL with the timescaledb extension. Set TIMESCALE_ENABLED=True
    first. The panel should be stopped: converting a table takes an exclusive
    lock on it. Safe to re-run.
    """
    if not TIMESCALE_ENABLED:
        utils.error(
            "TIMESCALE_ENABLED is not set. Add TIMESCALE_ENABLED=True to the .env file "
            "to confirm that this database is meant to run on TimescaleDB."
        )

    console.print(f"[bold]Database:[/bold] {transfer.describe(DATABASE_URI)}")

    if retention_days > 0:
        console.print(
            f"[yellow]Warning:[/yellow] raw usage rows older than {retention_days} days will be "
            "deleted permanently. The daily aggregates keep their totals, but per-hour detail "
            "is lost."
        )

    if not yes_to_all:
        typer.confirm(
            "The panel should be stopped before continuing. Proceed?", abort=True
        )

    engine = transfer.make_engine(DATABASE_URI)
    try:
        try:
            log = timescale.setup(
                engine,
                chunk_days=chunk_days,
                compress_after_days=compress_after_days,
                retention_days=retention_days,
                aggregates=not skip_aggregates,
            )
        except RuntimeError as exc:
            utils.error(str(exc))
            return
        except Exception as exc:
            utils.error(f"Setup failed: {exc}")
            return

        for line in log:
            console.print(f"  {line}")

        utils.success("TimescaleDB is set up. Start the panel again.", auto_exit=False)
    finally:
        engine.dispose()
