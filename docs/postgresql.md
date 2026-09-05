# Running Marzban on PostgreSQL / TimescaleDB

Marzban supports SQLite (default), MySQL and PostgreSQL. On PostgreSQL the usage
tables can additionally be turned into TimescaleDB hypertables, which keeps the
traffic history cheap to store and fast to chart.

Nothing here happens automatically. The panel keeps using whatever
`SQLALCHEMY_DATABASE_URL` points at, and TimescaleDB is applied by an explicit
CLI command.

## 1. Requirements

- PostgreSQL 13 or newer, with the `citext` extension available. `citext` ships
  with PostgreSQL itself (`postgresql-contrib` on Debian/Ubuntu) and is present
  in the official `postgres` and `timescale/timescaledb` images.
- For hypertables: the `timescaledb` extension, i.e. a
  `timescale/timescaledb:latest-pg16` image or the TimescaleDB packages.
- A recent panel image: PostgreSQL support and the `db` CLI commands are only in
  builds that include the changes described here.

`citext` is required because `users.username` and `nodes.name` are
case-insensitive. SQLite gets that from the `NOCASE` collation, which does not
exist on PostgreSQL; `CITEXT` is the portable equivalent.

## 2. Start a database

With the bundled overlay, having set `POSTGRES_PASSWORD` in `.env`:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d db
```

Or standalone:

```bash
docker run -d --name marzban-db --restart always \
  -p 127.0.0.1:5432:5432 \
  -e POSTGRES_USER=marzban \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=marzban \
  -v /var/lib/marzban-db:/var/lib/postgresql/data \
  timescale/timescaledb:latest-pg16
```

The extensions have to exist in the database that will be used. The panel
creates `citext` on its first connection when it has the rights to; if the user
is not a superuser, create it by hand:

```bash
docker exec -it marzban-db psql -U marzban -d marzban \
  -c "CREATE EXTENSION IF NOT EXISTS citext;"
```

## 3. Copy the data over

Back up first. The migration only reads from the source, but a copy costs
nothing:

```bash
cp /var/lib/marzban/db.sqlite3 /var/lib/marzban/db.sqlite3.bak
```

Stop the panel. Rows written while the copy runs are not picked up:

```bash
marzban down
```

Do a dry run against a throwaway database first, using the backup as the source:

```bash
marzban cli db migrate \
  --from "sqlite:////var/lib/marzban/db.sqlite3.bak" \
  --to "postgresql://marzban:secret@127.0.0.1:5432/marzban_test"
```

Then the real one:

```bash
marzban cli db migrate --to "postgresql://marzban:secret@127.0.0.1:5432/marzban"
```

The command creates the schema from the current models, stamps the Alembic
revision, copies every table in dependency order, fixes the sequences, and
compares row counts and traffic totals on both sides. It refuses to write into a
database that already holds Marzban tables unless `--force` is given, and exits
non-zero if the verification does not match.

## 4. Switch the panel over

Edit `/opt/marzban/.env`:

```env
SQLALCHEMY_DATABASE_URL = "postgresql://marzban:secret@127.0.0.1:5432/marzban"
```

Then:

```bash
marzban up
marzban cli db status
```

To roll back, put the old value back and restart. The SQLite file is untouched,
so it stays a working fallback. Keep it until the new database has run for a
while.

## 5. Enable TimescaleDB (optional)

Add to `.env`:

```env
TIMESCALE_ENABLED = True
```

Stop the panel, then:

```bash
marzban down
marzban cli db timescale-setup
marzban up
marzban cli db timescale-status
```

This converts `node_user_usages` and `node_usages` into hypertables, keeping the
rows already in them, creates the `node_user_usages_daily` and
`node_usages_daily` continuous aggregates, and registers a compression policy.
It is safe to re-run.

The command takes an exclusive lock on the usage tables while converting them,
which is why the panel should be down. It is not a data migration: no rows are
lost, and the panel works exactly the same afterwards, because hypertables are
ordinary tables as far as SQL is concerned.

`user_usage_logs` is left alone on purpose: it gains one row per traffic reset,
and its time column is nullable, so partitioning it would only add overhead.

### Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `TIMESCALE_ENABLED` | `False` | Confirms the database is meant for TimescaleDB. Required by `timescale-setup`. |
| `TIMESCALE_CHUNK_INTERVAL_DAYS` | `7` | Time span of one chunk. |
| `TIMESCALE_COMPRESS_AFTER_DAYS` | `30` | Compress chunks older than this. `0` disables compression. |
| `TIMESCALE_RETENTION_DAYS` | `0` | Delete raw usage rows older than this. `0` keeps everything. |

Retention is off by default because it destroys history. With it enabled, the
per-hour rows are dropped while the daily aggregates keep their totals, so the
long-range charts survive but the hourly detail does not.

Compression only applies to chunks older than `TIMESCALE_COMPRESS_AFTER_DAYS`,
while the usage jobs only ever write to the current hour, so the writes never
hit a compressed chunk.

## 6. Backups

SQLite backups were a file copy. On PostgreSQL:

```bash
docker exec -t marzban-db pg_dump -U marzban -Fc marzban > /var/lib/marzban/backup.dump
```

Restore into an empty database:

```bash
docker exec -i marzban-db pg_restore -U marzban -d marzban --clean --if-exists < /var/lib/marzban/backup.dump
```

With TimescaleDB, restore into a database where the `timescaledb` extension is
installed, and follow the TimescaleDB restore notes for hypertables.

## 7. Troubleshooting

**`collation "NOCASE" for encoding "UTF8" does not exist`** — the panel is on an
older build. Update the image.

**`could not open extension control file .../citext.control`** — the contrib
package is missing. Install `postgresql-contrib-<version>` or use the official
images.

**`permission denied to create extension`** — the database user is not a
superuser. Run the `CREATE EXTENSION` statements manually as `postgres`.

**`The timescaledb extension is not available on this server`** — the running
image is plain PostgreSQL. Switch to a `timescale/timescaledb` image; the data
directory is compatible for the same major version, but read the TimescaleDB
notes before swapping images in place.

**Verification mismatch after `migrate`** — do not switch the panel over. The
source is intact; drop the target database, check that the panel was really
stopped, and run the copy again.
