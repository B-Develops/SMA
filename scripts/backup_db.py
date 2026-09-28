#!/usr/bin/env python3
"""PostgreSQL backup for SarkinMota.

Creates a custom-format ``pg_dump`` archive, which can be compressed,
restored selectively, and inspected with ``pg_restore -l``.

Usage:
    python scripts/backup_db.py                      # Back up DATABASE_URL
    python scripts/backup_db.py --output C:/dump.dump
    python scripts/backup_db.py --retention 30
    python scripts/backup_db.py --db-url postgresql://user:pass@host:5432/db

Requires the PostgreSQL client tools (pg_dump) on PATH. Install them from
https://www.postgresql.org/download/ -- the pgAdmin installer bundles them.
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, unquote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
POSTGRES_SCHEMES = ("postgresql://", "postgres://")


class PostgresConnectionError(RuntimeError):
    """Raised when the connection details cannot be parsed or used."""


def parse_postgres_url(database_url):
    """Split a PostgreSQL URL into the pieces pg_dump needs.

    The password is returned separately so it can be passed through the
    PGPASSWORD environment variable rather than appearing in the process
    command line, where any other user on the box could read it from /proc.
    """
    if not database_url or not database_url.startswith(POSTGRES_SCHEMES):
        scheme = database_url.split(":", 1)[0] if database_url else "<empty>"
        raise PostgresConnectionError(
            f"PostgreSQL is the only supported backend; got scheme {scheme!r}."
        )

    parsed = urlparse(database_url)
    database = parsed.path.lstrip("/")
    if not database:
        raise PostgresConnectionError(f"No database name in {database_url!r}")

    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": unquote(parsed.username or "postgres"),
        "password": unquote(parsed.password or ""),
        "database": database,
    }


def _pg_env(password):
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    return env


def _run_pg_tool(tool, conn, extra_args, error_label):
    if shutil.which(tool) is None:
        raise PostgresConnectionError(
            f"{tool} not found on PATH. Install the PostgreSQL client tools "
            f"(https://www.postgresql.org/download/)."
        )

    cmd = [
        tool,
        "-h", conn["host"],
        "-p", conn["port"],
        "-U", conn["user"],
        "-d", conn["database"],
        *extra_args,
    ]
    # Passwords with shell metacharacters are safe here: subprocess passes the
    # argument list directly to CreateProcess without a shell.
    result = subprocess.run(
        cmd, env=_pg_env(conn["password"]), capture_output=True, text=True
    )
    if result.returncode != 0:
        raise PostgresConnectionError(
            f"{error_label} failed: {(result.stderr or result.stdout).strip()}"
        )
    return result


def check_connectivity(database_url):
    """Verify the server is reachable and the credentials work."""
    conn = parse_postgres_url(database_url)
    result = _run_pg_tool("pg_isready", conn, ["-q"], "pg_isready")
    return result.returncode == 0


def backup_postgresql(database_url, backup_path):
    """Write a custom-format dump of the database to ``backup_path``."""
    conn = parse_postgres_url(database_url)

    parent = os.path.dirname(os.path.abspath(backup_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    # -Fc custom format; --no-owner/--no-acl so the archive can be restored as
    # another role. pg_dump already reads a single consistent snapshot, so no
    # transaction flag is needed here (--single-transaction is a pg_restore
    # option, not a pg_dump one).
    _run_pg_tool(
        "pg_dump",
        conn,
        [
            "-Fc",
            "--no-owner",
            "--no-acl",
            "-f", os.path.abspath(backup_path),
        ],
        "pg_dump",
    )

    size = os.path.getsize(backup_path)
    if size == 0:
        raise PostgresConnectionError(f"pg_dump produced an empty file: {backup_path}")

    logger.info("PostgreSQL backup created: %s (%s bytes)", backup_path, size)
    return True


def cleanup_old_backups(backup_dir, retention_days, suffix=".dump"):
    """Remove backups older than ``retention_days``."""
    cutoff = (datetime.now() - timedelta(days=retention_days)).timestamp()
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return

    count = 0
    for file in backup_path.glob(f"*{suffix}"):
        try:
            if file.stat().st_mtime < cutoff:
                file.unlink()
                count += 1
        except OSError as exc:  # pragma: no cover - best effort cleanup
            logger.warning("Could not remove %s: %s", file, exc)

    if count:
        logger.info("Removed %d old backup(s)", count)


def main():
    parser = argparse.ArgumentParser(description="SarkinMota PostgreSQL Backup")
    parser.add_argument("--output", default=None, help="Backup file path")
    parser.add_argument(
        "--retention", type=int, default=30, help="Days to retain (default: 30)"
    )
    parser.add_argument(
        "--db-url", default=None, help="Database URL (default: $DATABASE_URL)"
    )
    args = parser.parse_args()

    database_url = args.db_url or os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("No database URL. Set DATABASE_URL or pass --db-url.")
        sys.exit(1)

    try:
        conn = parse_postgres_url(database_url)
    except PostgresConnectionError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"{conn['database']}_{timestamp}.dump"
    backup_dir = str(REPO_ROOT / "backups")
    backup_path = args.output or os.path.join(backup_dir, default_filename)

    logger.info("Starting PostgreSQL backup -> %s", backup_path)

    try:
        backup_postgresql(database_url, backup_path)
    except PostgresConnectionError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    cleanup_old_backups(os.path.dirname(os.path.abspath(backup_path)), args.retention)
    logger.info("Backup completed successfully")


if __name__ == "__main__":
    main()
