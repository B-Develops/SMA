#!/usr/bin/env python3
"""
Database backup script for SarkinMota.
Supports SQLite (default) and PostgreSQL (via DATABASE_URL).
Usage:
    python scripts/backup_db.py                  # Backup to default location
    python scripts/backup_db.py --output /path   # Custom backup path
    python scripts/backup_db.py --retention 30   # Keep backups for 30 days
"""

import os
import sys
import shutil
import sqlite3
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def backup_sqlite(db_path: str, backup_path: str) -> bool:
    """Create a backup of an SQLite database using the backup API."""
    try:
        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}")
            return False

        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(backup_path)
        src.backup(dst)
        dst.close()
        src.close()

        logger.info(f"SQLite backup created: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"SQLite backup failed: {e}")
        return False


def backup_postgresql(database_url: str, backup_path: str) -> bool:
    """Create a backup of a PostgreSQL database using pg_dump."""
    try:
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        # Parse DATABASE_URL (format: postgresql://user:pass@host:port/dbname)
        from urllib.parse import urlparse
        parsed = urlparse(database_url)

        if parsed.scheme not in ("postgresql", "postgres"):
            logger.error(f"Unsupported database scheme: {parsed.scheme}")
            return False

        env = os.environ.copy()
        env["PGPASSWORD"] = parsed.password or ""

        cmd = [
            "pg_dump",
            "-h", parsed.hostname or "localhost",
            "-p", str(parsed.port or 5432),
            "-U", parsed.username or "postgres",
            "-d", parsed.path.lstrip("/"),
            "-F", "c",
            "-f", backup_path,
        ]

        import subprocess
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return False

        logger.info(f"PostgreSQL backup created: {backup_path}")
        return True
    except FileNotFoundError:
        logger.error("pg_dump not found. Install PostgreSQL client tools.")
        return False
    except Exception as e:
        logger.error(f"PostgreSQL backup failed: {e}")
        return False


def cleanup_old_backups(backup_dir: str, retention_days: int) -> None:
    """Remove backups older than retention_days."""
    cutoff = datetime.now() - timedelta(days=retention_days)
    backup_path = Path(backup_dir)

    if not backup_path.exists():
        return

    count = 0
    for file in backup_path.glob("*.bak*"):
        if file.stat().st_mtime < cutoff.timestamp():
            file.unlink()
            count += 1

    if count:
        logger.info(f"Removed {count} old backup(s)")


def main():
    parser = argparse.ArgumentParser(description="SarkinMota Database Backup")
    parser.add_argument(
        "--output",
        default=None,
        help="Backup file path (default: backups/ directory with timestamp)"
    )
    parser.add_argument(
        "--retention",
        type=int,
        default=30,
        help="Days to retain backups (default: 30)"
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help="Database URL (default: from DATABASE_URL env or SQLite fallback)"
    )
    args = parser.parse_args()

    database_url = args.db_url or os.environ.get("DATABASE_URL", "sqlite:///sarkin_mota.db")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        db_name = database_url.split("/")[-1] or "sarkinmota"
        default_filename = f"{db_name}_{timestamp}.dump"
    else:
        default_filename = f"sarkin_mota_{timestamp}.bak"

    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
    backup_path = args.output or os.path.join(backup_dir, default_filename)

    logger.info(f"Starting backup -> {backup_path}")

    if database_url.startswith("postgresql://") or database_url.startswith("postgres://"):
        success = backup_postgresql(database_url, backup_path)
    else:
        db_file = database_url.replace("sqlite:///", "").replace("sqlite://", "")
        if not os.path.isabs(db_file):
            db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), db_file)
        success = backup_sqlite(db_file, backup_path)

    if success:
        cleanup_old_backups(os.path.dirname(backup_path), args.retention)
        logger.info("Backup completed successfully")
    else:
        logger.error("Backup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
