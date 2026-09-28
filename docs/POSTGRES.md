# PostgreSQL setup

SarkinMota runs on **PostgreSQL only**. SQLite support has been removed: the
app refuses to start with a non-PostgreSQL `DATABASE_URL`, money is stored as
`NUMERIC(14, 2)`, and the test suite runs against a real PostgreSQL server.

---

## 1. Install PostgreSQL (Windows)

Download the EDB installer from <https://www.postgresql.org/download/windows/>
and install PostgreSQL 16 or newer. The installer bundles the client tools
(`psql`, `pg_dump`, `pg_restore`) and optionally installs pgAdmin.

If you already have PostgreSQL, skip to step 2.

## 2. Create the databases

Open **SQL Shell (psql)** from the Start menu, or run `psql` in a terminal and
accept the default `postgres` superuser.

```sql
-- Application database
CREATE USER sarkinmota WITH PASSWORD 'change-me';
CREATE DATABASE sarkinmota OWNER sarkinmota;

-- Test database (the suite drops and recreates this schema on every run)
CREATE DATABASE sarkinmota_test OWNER sarkinmota;
```

> The test database name **must** contain `sarkinmota` — `tests/conftest.py`
> refuses to run otherwise, so you cannot accidentally destroy production data.

## 3. Configure the app

```bash
copy .env.example .env      # PowerShell
cp .env.example .env        # bash
```

Edit `.env`:

```dotenv
DATABASE_URL=postgresql://sarkinmota:change-me@localhost:5432/sarkinmota
```

**Percent-encode special characters in the password.** A Windows password
containing `@`, `/`, `#` or `:` will otherwise be parsed as URL structure:

| Character | Encoded |
| --------- | ------- |
| `@`       | `%40`   |
| `/`       | `%2F`   |
| `:`       | `%3A`   |
| `#`       | `%23`   |

Easiest fix: set a password with letters, digits and underscores only.

## 4. Create the schema

```bash
pip install -r requirements.txt
python init_db.py
```

This creates every table from the models and stamps the Alembic chain, so
subsequent `flask db upgrade` runs start from the current head.

To build the schema purely from migrations instead (equivalent result):

```bash
flask db upgrade
```

Both paths work on a brand new database. The initial migration was
re-baselined so the chain can be replayed from zero.

To check the two agree before you have a server, run `pytest
tests/test_migrations.py` — it replays the chain offline and diffs the result
against the models.

## 5. Run

```bash
python run.py
```

Check the connection at any time:

```
GET /health
```

```json
{
  "status": "healthy",
  "checks": {
    "database": {
      "status": "connected",
      "engine": "postgresql",
      "server_version": "16.4",
      "latency_ms": 1.42
    }
  }
}
```

---

## Running the tests

```bash
pip install -r requirements-dev.txt

# PowerShell
$env:TEST_DATABASE_URL = "postgresql://sarkinmota:change-me@localhost:5432/sarkinmota_test"
# bash
export TEST_DATABASE_URL="postgresql://sarkinmota:change-me@localhost:5432/sarkinmota_test"

pytest
```

`tests/test_backup.py` additionally needs `pg_dump`, `pg_restore` and `psql` on
`PATH`; it skips itself if they are missing.

`tests/test_migrations.py` needs **no database server** — it replays the
migration chain in Alembic's offline mode and asserts the resulting schema
matches the models, so it runs (and passes) even before PostgreSQL is
installed. It is the fastest way to catch schema drift:

```bash
pytest tests/test_migrations.py
```

---

## Backups and restores

```bash
python scripts/backup_db.py                    # backups/sarkinmota_<timestamp>.dump
python scripts/backup_db.py --retention 14
python scripts/backup_db.py --output D:/sm.dump

python scripts/restore_db.py backups/sarkinmota_20260927_120000.dump --list
python scripts/restore_db.py backups/sarkinmota_20260927_120000.dump
```

Backups are custom-format `pg_dump` archives taken in a single transaction, so
an archive is never a torn snapshot. A restore over a non-empty database is
refused unless you pass `--force`, because `pg_restore --clean` drops the
existing objects.

Scheduled backups: `scripts/schedule_backup.py` (Windows Task Scheduler
wrapper). Retention is enforced by the `--retention` flag.

---

## Importing data from a legacy SQLite file

One-time cutover helper. The app itself no longer reads SQLite.

```bash
python scripts/migrate_sqlite_to_postgres.py --sqlite sarkin_mota.db --dry-run
python scripts/migrate_sqlite_to_postgres.py --sqlite sarkin_mota.db
```

It copies each table through the SQLAlchemy models in foreign-key order and
then advances every sequence past the imported ids, so the next `INSERT` cannot
collide with a legacy primary key. Re-run with `--truncate` to start over.
Delete the script once you no longer need the old file.

---

## Docker

```bash
docker compose up -d
```

Compose starts `postgres:16-alpine` with a healthcheck, so the `web` container
waits for the database to finish `initdb` before its startup migration runs.
Override `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` in `.env` for
anything beyond local use — the defaults in the file are deliberately weak.

---

## Connection pool

`DATABASE_URL` is read once at startup and the pool is configured in
`app/__init__.py`. Tunables (all optional):

| Variable | Default | Notes |
| --- | --- | --- |
| `DB_POOL_SIZE` | `5` | **Per gunicorn worker.** Keep `workers × pool_size` well under `max_connections` (100 by default). |
| `DB_MAX_OVERFLOW` | `10` | Extra connections allowed when the pool is exhausted. |
| `DB_POOL_TIMEOUT` | `30` | Seconds to wait for a connection before raising. |
| `DB_POOL_RECYCLE` | `1800` | Recycle sockets before proxies or managed providers time them out. |
| `DB_STATEMENT_TIMEOUT_MS` | `30000` | Aborts runaway queries instead of pinning a pooled connection forever. |

To raise PostgreSQL's own limit:

```sql
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
```

---

## Managed PostgreSQL

Supabase, Neon, Render and RDS all work. Two things to change:

1. Use the provider's pooled (transaction-mode) URL for the app, which usually
   looks like `postgresql://user:pass@host/db?sslmode=require`. The `?sslmode=`
   query parameter is passed through to psycopg2 automatically.
2. Lower `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` — pooled providers cap total
   connections aggressively, and a per-worker pool of 15 will exhaust them.
   For example `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=3`.

Providers using PgBouncer in transaction mode are not compatible with server-side
prepared statements. If you hit `prepared statement "s0" already exists`, switch
to the session pooler or add `?pgbouncer=true` with SQLAlchemy's psycopg2
dialect.

---

## What changed

- `app/__init__.py` — `DATABASE_URL` is validated and must be `postgresql://`;
  `postgres://` is rewritten. `SQLALCHEMY_DATABASE_URI` no longer falls back to
  SQLite. Engine options, pool tuning and a `statement_timeout` are applied
  unconditionally. `/health` reports the PostgreSQL server version.
- `app/models.py` — money columns are `NUMERIC(14, 2)`. Status and flag columns
  are `NOT NULL` with a `server_default`, so raw `text()` inserts in
  `cars/routes.py` can no longer write `status = NULL`. Added `CHECK`
  constraints and indexes for the browse and dashboard query paths.
- `app/blueprints/cars/routes.py` — user-supplied amounts are parsed as
  `Decimal`, not `float`.
- `migrations/versions/6cf388f0ae84_initial_migration.py` — re-baselined to
  create the base tables, so `flask db upgrade` works on an empty server. This
  also adds `admin_action_logs`, which no migration had ever created: a database
  built from the chain alone was missing the table and would crash on the first
  admin audit write.
- `migrations/versions/c4e91b0a7d52_postgresql_schema.py` — new: type changes,
  nullability, constraints and indexes.
- `tests/test_migrations.py` — new. Verifies offline that the migration chain
  produces exactly the model schema, and that NULL flags are backfilled before
  going `NOT NULL`.
- `scripts/backup_db.py`, `scripts/restore_db.py` — PostgreSQL-only, with a
  `--list` mode and a guard against restoring over a populated database.
- `scripts/migrate_sqlite_to_postgres.py` — new one-time data importer.
- `tests/conftest.py` — runs against a real PostgreSQL server via
  `TEST_DATABASE_URL`.
- Deleted: `check_db.py`, `dbcheck.py`, `check_user.py`, `db_edit.py`,
  `export_admin_dashboard.py` (all dead scripts using the `sqlite3` stdlib or
  importing a non-existent `app.app`).
