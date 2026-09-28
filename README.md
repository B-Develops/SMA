# SMA — SarkinMota Autos

Car marketplace (Flask + PostgreSQL).

## Requirements

- Python 3.11+
- PostgreSQL 16+ (the only supported database)
- Redis (optional — caching and background email fall back to in-process and
  synchronous behaviour when it is absent)

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set `DATABASE_URL` plus `SECRET_KEY`:

```dotenv
DATABASE_URL=postgresql://sarkinmota:change-me@localhost:5432/sarkinmota
SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
```

Then create the schema and run:

```bash
python init_db.py
python run.py
```

## Tests

```bash
pip install -r requirements-dev.txt
export TEST_DATABASE_URL="postgresql://sarkinmota:change-me@localhost:5432/sarkinmota_test"
pytest
```

## Documentation

- [`docs/DEPLOY.md`](docs/DEPLOY.md) — deployment checklist, required
  environment variables, first-admin bootstrap, platform notes, and the
  post-deploy verification steps.
- [`docs/POSTGRES.md`](docs/POSTGRES.md) — PostgreSQL installation, schema
  creation, pool tuning, backups, data import, Docker and managed-PostgreSQL
  notes.
