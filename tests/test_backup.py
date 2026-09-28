"""Backup and restore roundtrip tests against a real PostgreSQL server.

These exercise scripts/backup_db.py and scripts/restore_db.py end to end, so
they need the PostgreSQL client tools (pg_dump, pg_restore, psql) on PATH in
addition to the server the rest of the suite needs. If the tools are missing
the tests skip rather than fail, so the suite still runs on a machine that only
has the server.
"""
import os
import shutil
import sys

import pytest

# Ensure scripts package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import db  # noqa: E402
from conftest import _test_database_url  # noqa: E402
from scripts.backup_db import parse_postgres_url  # noqa: E402
# Import the exception from restore_db (which re-exports backup_db's) so it is
# the same class object the restore path actually raises.
from scripts.restore_db import PostgresConnectionError  # noqa: E402

pytestmark = pytest.mark.usefixtures("_drop_public_schema")


def _require_pg_tools():
    missing = [t for t in ("pg_dump", "pg_restore", "psql") if shutil.which(t) is None]
    if missing:
        pytest.skip(
            f"PostgreSQL client tools not on PATH: {', '.join(missing)}. "
            "Install them from https://www.postgresql.org/download/."
        )


def _seed(db):
    """Insert one row of known data so the roundtrip has something to prove."""
    from app.models import User

    user = User(email="alice@example.com", password="x", name="Alice")
    db.session.add(user)
    db.session.commit()
    return user.id


def test_backup_creates_custom_format_dump(tmp_path, app):
    _require_pg_tools()
    from scripts.backup_db import backup_postgresql

    # Uses the app fixture so db.create_all() has populated the schema --
    # dumping an empty database would prove nothing.
    backup_path = str(tmp_path / "backup.dump")
    assert backup_postgresql(_test_database_url(), backup_path) is True
    assert os.path.exists(backup_path)
    assert os.path.getsize(backup_path) > 0

    # pg_restore -l only succeeds on a readable custom-format archive.
    import subprocess

    listing = subprocess.run(
        ["pg_restore", "-l", backup_path], capture_output=True, text=True
    )
    assert listing.returncode == 0
    assert "TABLE" in listing.stdout
    for table in ("users", "cars", "orders", "payments", "admin_action_logs"):
        assert table in listing.stdout, f"{table} missing from the dump"


def test_backup_then_restore_roundtrip(tmp_path, app):
    _require_pg_tools()
    from scripts.backup_db import backup_postgresql
    from scripts.restore_db import restore_postgresql

    with app.app_context():
        _seed(db)
        backup_path = str(tmp_path / "roundtrip.dump")
        assert backup_postgresql(_test_database_url(), backup_path) is True

        from app.models import User

        db.session.query(User).delete()
        db.session.commit()

        assert restore_postgresql(backup_path, _test_database_url(), force=True) is True

        emails = [u.email for u in User.query.all()]
        assert "alice@example.com" in emails


def test_restore_refuses_populated_database(tmp_path, app):
    """A restore over live data must be blocked unless --force is passed."""
    _require_pg_tools()
    from scripts.backup_db import backup_postgresql
    from scripts.restore_db import restore_postgresql

    with app.app_context():
        _seed(db)
        backup_path = str(tmp_path / "guarded.dump")
        assert backup_postgresql(_test_database_url(), backup_path) is True

        with pytest.raises(PostgresConnectionError) as exc:
            restore_postgresql(backup_path, _test_database_url(), force=False)
        assert "--force" in str(exc.value)


def test_restore_rejects_corrupt_archive(tmp_path):
    _require_pg_tools()
    from scripts.restore_db import restore_postgresql

    corrupt = tmp_path / "corrupt.dump"
    corrupt.write_bytes(b"this is not a pg_dump archive")

    with pytest.raises(PostgresConnectionError):
        restore_postgresql(str(corrupt), _test_database_url(), force=True)


def test_restore_missing_file_fails(tmp_path):
    from scripts.restore_db import restore_postgresql

    with pytest.raises(PostgresConnectionError):
        restore_postgresql(str(tmp_path / "nope.dump"), _test_database_url())


def test_non_postgres_url_is_rejected():
    """SarkinMota is PostgreSQL-only, so a sqlite URL must fail loudly."""
    from scripts.backup_db import parse_postgres_url

    with pytest.raises(PostgresConnectionError) as exc:
        parse_postgres_url("sqlite:///database.db")
    assert "PostgreSQL" in str(exc.value)


def test_money_survives_backup_as_exact_decimal(tmp_path, app):
    """NUMERIC must roundtrip exactly -- a float roundtrip would not."""
    _require_pg_tools()
    from decimal import Decimal
    from scripts.backup_db import backup_postgresql
    from scripts.restore_db import restore_postgresql
    from app.models import Car, User

    awkward = Decimal("1234567.89")

    with app.app_context():
        user = User(email="money@example.com", password="x", name="Money")
        db.session.add(user)
        db.session.flush()
        db.session.add(Car(seller_id=user.id, make="Honda", model="Civic",
                           year=2020, price=awkward, status="active"))
        db.session.commit()

        backup_path = str(tmp_path / "money.dump")
        assert backup_postgresql(_test_database_url(), backup_path) is True
        assert restore_postgresql(backup_path, _test_database_url(), force=True) is True

        price = db.session.query(Car.price).scalar()
        assert price == awkward
        assert isinstance(price, Decimal)
