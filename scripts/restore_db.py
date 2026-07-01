#!/usr/bin/env python3
"""
Database restore script for SarkinMota.
Supports SQLite and PostgreSQL backups created by backup_db.py.
Usage:
    python scripts/restore_db.py backups/sarkin_mota_20240101_120000.bak
    python scripts/restore_db.py backups/sarkinmota_20240101_120000.dump --db-url postgresql://...
"""

import os
import sys
import sqlite3
import argparse
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def restore_sqlite(backup_path: str, db_path: str) -> bool:
    """Restore an SQLite database from a backup file."""
    try:
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False

        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

        # Verify backup integrity first
        conn_check = sqlite3.connect(backup_path)
        conn_check.execute("SELECT name FROM sqlite_master WHERE type='table'")
        conn_check.close()

        # Restore by copying the backup file over the target
        shutil.copy2(backup_path, db_path)

        logger.info(f"SQLite database restored: {db_path}")
        return True
    except Exception as e:
        logger.error(f"SQLite restore failed: {e}")
        return False


def restore_postgresql(backup_path: str, database_url: str) -> bool:
    """Restore a PostgreSQL database from a custom-format dump."""
    try:
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False

        from urllib.parse import urlparse
        parsed = urlparse(database_url)

        if parsed.scheme not in ("postgresql", "postgres"):
            logger.error(f"Unsupported database scheme: {parsed.scheme}")
            return False

        env = os.environ.copy()
        env["PGPASSWORD"] = parsed.password or ""

        cmd = [
            "pg_restore",
            "-h", parsed.hostname or "localhost",
            "-p", str(parsed.port or 5432),
            "-U", parsed.username or "postgres",
            "-d", parsed.path.lstrip("/"),
            "-c",
            backup_path,
        ]

        import subprocess
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"pg_restore failed: {result.stderr}")
            return False

        logger.info(f"PostgreSQL database restored from: {backup_path}")
        return True
    except FileNotFoundError:
        logger.error("pg_restore not found. Install PostgreSQL client tools.")
        return False
    except Exception as e:
        logger.error(f"PostgreSQL restore failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="SarkinMota Database Restore")
    parser.add_argument("backup_file", help="Path to backup file")
    parser.add_argument(
        "--db-url",
        default=None,
        help="Database URL (default: from DATABASE_URL env or SQLite fallback)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    args = parser.parse_args()

    database_url = args.db_url or os.environ.get("DATABASE_URL", "sqlite:///sarkin_mota.db")

    if not args.force:
        confirm = input(
            f"WARNING: This will overwrite the current database.\n"
            f"Backup: {args.backup_file}\n"
            f"Target: {database_url}\n"
            "Type 'yes' to confirm: "
        )
        if confirm.strip().lower() != "yes":
            logger.info("Restore cancelled by user")
            sys.exit(0)

    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        success = restore_postgresql(args.backup_file, database_url)
    else:
        db_file = database_url.replace("sqlite:///", "").replace("sqlite://", "")
        if not os.path.isabs(db_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_file = os.path.join(base_dir, db_file)
        success = restore_sqlite(args.backup_file, db_file)

    if not success:
        logger.error("Restore failed")
        sys.exit(1)

    logger.info("Restore completed successfully")


if __name__ == "__main__":
    main()
