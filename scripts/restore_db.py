#!/usr/bin/env python3
"""Restore a PostgreSQL database from a backup created by backup_db.py.

Usage:
    python scripts/restore_db.py backups/sarkinmota_20260927_120000.dump
    python scripts/restore_db.py backup.dump --db-url postgresql://user:pass@host/db
    python scripts/restore_db.py backup.dump --target-db sarkinmota_staging

By default the restore is refused if the target already has tables, because
pg_restore --clean drops existing objects. Pass --force to restore over a
populated database, and --list to inspect an archive without touching anything.
"""

import argparse
import logging
import os
import subprocess
import sys

# Import the shared helpers under one canonical module name. When run as
# `python scripts/restore_db.py` only the scripts/ directory is on sys.path, so
# fall back to a top-level import. Mixing the two would load backup_db.py twice
# and create two distinct PostgresConnectionError classes, so a caller catching
# one would miss errors raised from the other.
try:
    from scripts.backup_db import (
        PostgresConnectionError,
        _pg_env,
        _run_pg_tool,
        parse_postgres_url,
    )
except ImportError:  # executed as a script
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from backup_db import (  # type: ignore[no-redef]
        PostgresConnectionError,
        _pg_env,
        _run_pg_tool,
        parse_postgres_url,
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def _list_tables(conn):
    """Return the user tables present in the target database."""
    result = _run_pg_tool(
        "psql",
        conn,
        [
            "-tAc",
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = current_schema() AND tablename <> 'alembic_version'",
        ],
        "psql",
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def inspect_backup(backup_path):
    """Print the archive contents (equivalent to ``pg_restore -l``)."""
    if not os.path.exists(backup_path):
        raise PostgresConnectionError(f"Backup file not found: {backup_path}")

    result = subprocess.run(
        ["pg_restore", "-l", backup_path], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise PostgresConnectionError(
            f"pg_restore could not read {backup_path}: "
            f"{(result.stderr or result.stdout).strip()}"
        )
    print(result.stdout)
    return True


def restore_postgresql(backup_path, database_url, force=False):
    """Restore ``backup_path`` into the database named by ``database_url``."""
    if not os.path.exists(backup_path):
        raise PostgresConnectionError(f"Backup file not found: {backup_path}")

    conn = parse_postgres_url(database_url)

    existing = _list_tables(conn)
    if existing and not force:
        raise PostgresConnectionError(
            f"Target database {conn['database']!r} already contains "
            f"{len(existing)} table(s) (e.g. {', '.join(existing[:3])}). "
            "Restoring would drop them. Re-run with --force to overwrite."
        )

    # --clean --if-exists drops each object only if it is present, so a restore
    # works against both an empty and a populated database.
    _run_pg_tool(
        "pg_restore",
        conn,
        [
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-acl",
            "--single-transaction",
            os.path.abspath(backup_path),
        ],
        "pg_restore",
    )

    logger.info("PostgreSQL database restored from: %s", backup_path)
    return True


def main():
    parser = argparse.ArgumentParser(description="SarkinMota PostgreSQL Restore")
    parser.add_argument("backup_file", help="Path to a .dump backup file")
    parser.add_argument(
        "--db-url", default=None, help="Database URL (default: $DATABASE_URL)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Restore over a populated database"
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_only", help="Show archive contents and exit"
    )
    args = parser.parse_args()

    try:
        if args.list_only:
            sys.exit(0 if inspect_backup(args.backup_file) else 1)

        database_url = args.db_url or os.environ.get("DATABASE_URL")
        if not database_url:
            logger.error("No database URL. Set DATABASE_URL or pass --db-url.")
            sys.exit(1)

        if not args.force:
            conn = parse_postgres_url(database_url)
            confirm = input(
                f"WARNING: this overwrites the contents of "
                f"{conn['host']}/{conn['database']}.\n"
                f"Backup: {args.backup_file}\n"
                "Type 'yes' to continue: "
            )
            if confirm.strip().lower() != "yes":
                logger.info("Restore cancelled.")
                sys.exit(0)

        restore_postgresql(args.backup_file, database_url, force=args.force)
    except PostgresConnectionError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    logger.info("Restore completed successfully")


if __name__ == "__main__":
    main()
