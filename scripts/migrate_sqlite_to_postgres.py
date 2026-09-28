#!/usr/bin/env python3
"""One-time import of a legacy SQLite database into PostgreSQL.

The app itself no longer supports SQLite, so this is the only remaining
reader of a ``.db`` file. It exists purely to carry data across during the
cutover and can be deleted once you have migrated.

It reads the legacy file with the stdlib ``sqlite3`` module (read-only, so a
mistake cannot corrupt the source) and writes every row through the SQLAlchemy
models, so the target is populated with exactly the same defaults,
constraints and cascading behaviour the app expects.

Usage:
    python scripts/migrate_sqlite_to_postgres.py --sqlite sarkin_mota.db
    python scripts/migrate_sqlite_to_postgres.py --sqlite sarkin_mota.db --dry-run
    python scripts/migrate_sqlite_to_postgres.py --sqlite old.db --truncate

Tables are copied in foreign-key order. Rows whose parent is missing are
skipped and reported rather than aborting the whole import, so one bad record
cannot cost you the rest of the database.
"""

import argparse
import logging
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db  # noqa: E402
from app.models import (  # noqa: E402
    AdminActionLog,
    Car,
    Notification,
    NotificationSettings,
    Order,
    PasswordResetToken,
    Payment,
    SavedCar,
    User,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# (table, model, parent table or None). Order matters: parents before children.
COPY_ORDER = [
    ("users", User, None),
    ("cars", Car, "users"),
    ("orders", Order, "cars"),
    ("payments", Payment, "orders"),
    ("saved_cars", SavedCar, "cars"),
    ("notifications", Notification, "users"),
    ("notification_settings", NotificationSettings, "users"),
    ("password_reset_tokens", PasswordResetToken, "users"),
    ("admin_action_logs", AdminActionLog, "users"),
]

# Columns the legacy SQLite files may not have, or may have drifted from.
SKIP_COLUMNS = {"bids"}


def _sqlite_columns(conn, table):
    try:
        return {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}
    except sqlite3.DatabaseError:
        return set()


def _model_columns(model):
    return {c.name for c in model.__table__.columns}


def _existing_tables(conn):
    return {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def _read_rows(conn, table, columns):
    cols = ", ".join(f'"{c}"' for c in sorted(columns))
    cur = conn.execute(f'SELECT {cols} FROM "{table}"')
    names = [d[0] for d in cur.description]
    for row in cur:
        yield dict(zip(names, row))


def migrate(sqlite_path, dry_run=False, truncate=False, batch_size=500):
    if not os.path.exists(sqlite_path):
        raise SystemExit(f"SQLite file not found: {sqlite_path}")

    app = create_app()

    with app.app_context():
        engine = db.engine
        if engine.dialect.name != "postgresql":
            raise SystemExit(
                f"Target must be PostgreSQL, got {engine.dialect.name!r}. "
                "Set DATABASE_URL in your .env file."
            )
        logger.info("Target: %s", engine.url.render_as_string(hide_password=True))

        # mode=ro refuses to create or modify the legacy file.
        source = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
        source.row_factory = sqlite3.Row
        try:
            present = _existing_tables(source)
            if not present:
                raise SystemExit(f"No tables found in {sqlite_path}.")

            total = 0
            for table, model, parent in COPY_ORDER:
                if table not in present:
                    logger.info("Skipping %s: not present in source", table)
                    continue

                sqlite_cols = _sqlite_columns(source, table)
                model_cols = _model_columns(model)
                shared = (sqlite_cols & model_cols) - SKIP_COLUMNS
                dropped = sorted(sqlite_cols - model_cols)
                if dropped:
                    logger.warning("%s: ignoring unknown columns %s", table, dropped)
                if not shared:
                    logger.warning("%s: no shared columns, skipping", table)
                    continue

                rows = list(_read_rows(source, table, shared))
                if not rows:
                    logger.info("%s: 0 rows", table)
                    continue

                if dry_run:
                    logger.info("[dry-run] %s: %d rows -> %s", table, len(rows), table)
                    total += len(rows)
                    continue

                if truncate:
                    db.session.query(model).delete()
                    db.session.commit()

                inserted = 0
                for offset in range(0, len(rows), batch_size):
                    chunk = rows[offset:offset + batch_size]
                    # Legacy primary keys are carried over verbatim, so the
                    # foreign key values already present in the child tables
                    # point at the right parents. Only the sequences need
                    # fixing up afterwards.
                    for row in chunk:
                        obj = model()
                        for col, value in row.items():
                            setattr(obj, col, value)
                        db.session.add(obj)
                    try:
                        db.session.commit()
                    except Exception as exc:
                        db.session.rollback()
                        logger.error(
                            "%s: batch starting at row %d failed: %s",
                            table, offset, exc,
                        )
                        break
                    inserted += len(chunk)

                total += inserted
                logger.info("%s: imported %d/%d rows", table, inserted, len(rows))

            if dry_run:
                logger.info("[dry-run] %d rows would be imported", total)
                return total

            _reset_sequences()
            db.session.commit()
            logger.info("Import complete: %d rows", total)
            return total
        finally:
            source.close()


def _reset_sequences():
    """Advance every serial sequence past the highest imported id.

    Without this the next INSERT collides with an imported row's primary key.
    setval is called with is_called=false so the next value is exactly
    max(id) + 1.
    """
    from sqlalchemy import text

    for table in (
        "users", "cars", "orders", "payments", "saved_cars",
        "notifications", "notification_settings",
        "password_reset_tokens", "admin_action_logs",
    ):
        db.session.execute(
            text(
                f"SELECT setval("
                f"  pg_get_serial_sequence('{table}', 'id'),"
                f"  COALESCE((SELECT MAX(id) FROM \"{table}\"), 1),"
                f"  (SELECT MAX(id) IS NOT NULL FROM \"{table}\")"
                f")"
            )
        )
    logger.info("Sequences advanced past imported ids.")


def main():
    parser = argparse.ArgumentParser(
        description="Import a legacy SQLite database into PostgreSQL"
    )
    parser.add_argument(
        "--sqlite",
        default="sarkin_mota.db",
        help="Path to the legacy SQLite file (default: sarkin_mota.db)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report counts without writing"
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Empty each target table before importing (re-running the import)",
    )
    args = parser.parse_args()

    migrate(args.sqlite, dry_run=args.dry_run, truncate=args.truncate)


if __name__ == "__main__":
    main()
