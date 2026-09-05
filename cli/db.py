import typer
from rich.console import Console
from rich.table import Table

from app.db import transfer
from app.db.base import DATABASE_URI

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
