"""Schema consistency: the migration chain must match the models.

The migration history is not a clean mirror of the models -- the base tables
and admin_action_logs were originally only ever created by db.create_all(), so
a database built purely from `flask db upgrade` was missing them. This test
runs the chain in Alembic's offline mode (no database server required, because
`op.get_bind()` is a mock there) and diffs the emitted DDL against
db.metadata, so that class of drift fails loudly instead of at runtime.

It also asserts every money column is retyped to NUMERIC(14, 2); a
double-precision column cannot represent kobo exactly, so summed order amounts
drift.
"""
import os
import re
import subprocess
import sys

import pytest
import sqlalchemy as sa

from app import db
import app.models  # noqa: F401  (registers all models)

# Money columns are created as FLOAT in the initial migration and retyped by a
# later revision.
MONEY_COLUMNS = [
    ("cars", "price"),
    ("orders", "order_amount"),
    ("orders", "listed_price"),
    ("payments", "amount"),
]


def _generate_migration_sql():
    """Run `flask db upgrade --sql` and return the emitted DDL."""
    env = {**os.environ, "PYTHONWARNINGS": "ignore"}
    env.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/sarkinmota")
    proc = subprocess.run(
        [
            sys.executable, "-m", "flask",
            "--app", "app:create_app", "db", "upgrade", "--sql",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    assert proc.returncode == 0, (
        "Could not generate migration SQL offline:\n" + proc.stderr[-4000:]
    )
    return proc.stdout


@pytest.fixture(scope="module")
def migration_sql():
    return _generate_migration_sql()


@pytest.fixture(scope="module")
def migrated_tables(migration_sql):
    """Map of table name -> set of column names created by the chain."""
    tables = {}
    for match in re.finditer(r"CREATE TABLE (\w+) \((.*?)\n\);", migration_sql, re.S):
        name, body = match.group(1), match.group(2)
        cols = set()
        for line in body.split("\n"):
            line = line.strip().rstrip(",")
            if re.match(r"^(CONSTRAINT|PRIMARY KEY|FOREIGN KEY|UNIQUE|CHECK)", line):
                continue
            col = re.match(r"^(\w+)\s+\S", line)
            if col:
                cols.add(col.group(1))
        tables[name] = cols

    # Columns added by later revisions arrive as ALTER TABLE ... ADD COLUMN,
    # which the CREATE TABLE scan above does not see.
    for table, col in re.findall(r"ALTER TABLE (\w+) ADD COLUMN (\w+)", migration_sql):
        tables.setdefault(table, set()).add(col)

    tables.pop("alembic_version", None)
    return tables


def test_every_model_table_is_created_by_a_migration(migrated_tables):
    model_tables = {t.name for t in db.metadata.sorted_tables} - {"alembic_version"}
    missing = model_tables - set(migrated_tables)
    assert not missing, (
        f"Tables defined in the models but never created by any migration: "
        f"{sorted(missing)}. A database built with `flask db upgrade` would be "
        f"missing them."
    )


def test_no_migration_creates_an_unknown_table(migrated_tables):
    model_tables = {t.name for t in db.metadata.sorted_tables}
    extra = set(migrated_tables) - model_tables
    assert not extra, f"Migrations create tables that are not in the models: {sorted(extra)}"


def test_every_model_column_is_created_by_a_migration(migrated_tables):
    problems = []
    for table in db.metadata.sorted_tables:
        if table.name == "alembic_version":
            continue
        missing = set(table.columns.keys()) - migrated_tables.get(table.name, set())
        if missing:
            problems.append(f"{table.name}: {sorted(missing)}")
    assert not problems, "Columns in the models but not created by migrations: " + "; ".join(problems)


def test_every_model_index_and_unique_constraint_exists(migration_sql):
    created = set(re.findall(r"CREATE (?:UNIQUE )?INDEX (\w+) ON", migration_sql))
    # Inline UNIQUE(...) and ALTER TABLE ... ADD CONSTRAINT are the other two
    # ways a model-level constraint reaches the database.
    created |= set(re.findall(r"CONSTRAINT (\w+) UNIQUE", migration_sql))
    created |= set(re.findall(r"ADD CONSTRAINT (\w+) CHECK", migration_sql))

    expected = set()
    for table in db.metadata.sorted_tables:
        for index in table.indexes:
            expected.add(index.name)
        for constraint in table.constraints:
            if isinstance(constraint, (sa.UniqueConstraint, sa.CheckConstraint)) and constraint.name:
                expected.add(constraint.name)

    missing = expected - created
    assert not missing, f"Indexes/constraints in the models but not in migrations: {sorted(missing)}"


def test_money_columns_are_retyped_to_numeric(migration_sql):
    for table, column in MONEY_COLUMNS:
        assert re.search(
            r"ALTER TABLE %s ALTER COLUMN %s TYPE NUMERIC\(14, 2\)" % (table, column),
            migration_sql,
        ), (
            f"{table}.{column} is never retyped to NUMERIC(14, 2). A "
            f"double-precision column cannot represent kobo exactly."
        )


def test_status_and_flag_columns_get_not_null_and_server_defaults(migration_sql):
    """The raw INSERT in cars/routes.py omits `status`, so a server default is
    required -- a Python-side default alone leaves those rows NULL."""
    for table, column, default in (
        ("cars", "status", "active"),
        ("orders", "status", "pending"),
        ("users", "role", "user"),
    ):
        assert re.search(
            r'ALTER TABLE %s ALTER COLUMN %s SET NOT NULL' % (table, column), migration_sql
        ), f"{table}.{column} is never made NOT NULL"
        assert re.search(
            r"ALTER TABLE %s ALTER COLUMN %s SET DEFAULT '%s'" % (table, column, default),
            migration_sql,
        ), f"{table}.{column} has no server_default of '{default}'"


def test_null_flags_are_backfilled_before_going_not_null(migration_sql):
    """A legacy NULL would otherwise abort the NOT NULL change."""
    for table, column in (
        ("users", "role"),
        ("users", "email_verified"),
        ("cars", "status"),
        ("orders", "status"),
        ("payments", "status"),
        ("notifications", "is_read"),
    ):
        backfill = re.search(
            r'UPDATE "%s" SET "%s" = .*? WHERE "%s" IS NULL' % (table, column, column),
            migration_sql,
        )
        not_null = re.search(
            r"ALTER TABLE %s ALTER COLUMN %s SET NOT NULL" % (table, column), migration_sql
        )
        assert backfill and not_null, f"{table}.{column} missing backfill or NOT NULL"
        assert migration_sql.index(backfill.group(0)) < migration_sql.index(not_null.group(0)), (
            f"{table}.{column} is set NOT NULL before its NULLs are backfilled"
        )
