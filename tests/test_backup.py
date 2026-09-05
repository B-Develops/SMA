"""Backup and restore roundtrip tests."""
import os
import sys
import tempfile
import shutil
import sqlite3

import pytest

# Ensure scripts package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sqlite_db_with_data(tmp_path):
    """Create a temporary SQLite database with known data."""
    db_path = str(tmp_path / "source.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL)")
    conn.execute(
        "INSERT INTO users (email) VALUES ('alice@example.com'), ('bob@example.com')"
    )
    conn.commit()
    conn.close()
    return db_path


def test_sqlite_backup_creates_file(sqlite_db_with_data, tmp_path):
    from scripts.backup_db import backup_sqlite

    backup_path = str(tmp_path / "backup.bok")
    assert backup_sqlite(sqlite_db_with_data, backup_path) is True
    assert os.path.exists(backup_path)
    assert os.path.getsize(backup_path) > 0


def test_sqlite_backup_restore_roundtrip(sqlite_db_with_data, tmp_path):
    from scripts.backup_db import backup_sqlite
    from scripts.restore_db import restore_sqlite

    backup_path = str(tmp_path / "backup.bok")
    restore_path = str(tmp_path / "restored.db")

    assert backup_sqlite(sqlite_db_with_data, backup_path) is True
    assert restore_sqlite(backup_path, restore_path) is True

    conn = sqlite3.connect(restore_path)
    rows = conn.execute("SELECT email FROM users ORDER BY id").fetchall()
    conn.close()

    assert rows == [("alice@example.com",), ("bob@example.com",)]


def test_restore_verifies_backup_integrity(tmp_path):
    """Restore of a corrupt/empty file must fail gracefully."""
    from scripts.restore_db import restore_sqlite

    corrupt = str(tmp_path / "corrupt.bak")
    with open(corrupt, "wb") as f:
        f.write(b"not a sqlite database")

    target = str(tmp_path / "target.db")
    assert restore_sqlite(corrupt, target) is False
    assert not os.path.exists(target)


def test_backup_missing_source_fails(tmp_path):
    from scripts.backup_db import backup_sqlite

    assert backup_sqlite(str(tmp_path / "does-not-exist.db"), str(tmp_path / "b.bak")) is False
