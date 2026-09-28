# Deployment

Deployment-readiness notes for SarkinMota. Database setup is covered
separately in [`POSTGRES.md`](POSTGRES.md).

## Current status

The app is verified against a real PostgreSQL 16 server:

- 50/50 tests pass (`pytest`)
- The Alembic chain applies cleanly to an **empty** database
- `/health`, `/`, `/cars/browse`, `/mobile/browse-cars`, `/auth/login` and
  `/metrics` all return 200 under a live server
- `pg_dump` / `pg_restore` roundtrip proven, including exact `NUMERIC` money
  (`47500000.55` renders as `₦47,500,000.55`)

Two things are still not production-ready, both by design rather than defect —
see [Known gaps](#known-gaps).

---

## Required environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `DATABASE_URL` | **yes** | `postgresql://user:pass@host:5432/db`. `postgres://` is rewritten. Any other scheme **refuses to start**. |
| `SECRET_KEY` | **yes** | Production refuses to start without it. See below. |
| `FLASK_ENV` | **yes** | Must be `production` for the SECRET_KEY check and other prod behaviour. |
| `BASE_URL` | yes | Absolute URL used in email links and redirects. |
| `FORCE_HTTPS` | yes | `True` in production. Sets secure cookies and HSTS. |
| `HSTS` | recommended | `True` in production. |
| `UPLOAD_DIR` | **yes on PaaS** | Path to a persistent disk. Without it, uploaded car images are lost on every deploy. |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD` | for email | Booleans accept `1/true/yes/on`. |
| `REDIS_URL` | optional | Absent → in-process cache and synchronous email. |
| `MAX_UPLOAD_SIZE_MB` | optional | Default 16. |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, ... | optional | See [`POSTGRES.md`](POSTGRES.md#connection-pool). |

### SECRET_KEY is mandatory in production
The app will **not start** in production without it, and deliberately ignores a
`.secret_key` file if one exists. A file-based key is copied into the Docker
image by `COPY . .` and regenerates on every deploy, which silently logs out
every user and invalidates every CSRF token. `.dockerignore` and `.gitignore`
both exclude it.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set the same value across every instance and every deploy.

---

## First deploy

```bash
# 1. Point at a real database (NOT the SQLite fallback -- there isn't one)
export DATABASE_URL="postgresql://user:pass@host:5432/sarkinmota"
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export FLASK_ENV=production
export BASE_URL=https://yourdomain.com
export FORCE_HTTPS=True

# 2. Create the schema
python init_db.py

# 3. Bootstrap the first admin (a fresh deploy has no users, so
#    `promote-admin` has nothing to promote)
flask create-admin --email you@example.com --name "Site Admin" --password "..."
```

`create-admin` is idempotent — re-running it promotes an existing account
instead of failing.

### If your platform has no shell

Render's free tier does not provide a shell, so `flask create-admin` cannot be
run there. Instead, set these two env vars and the app creates the first admin
itself on the first boot:

```
ADMIN_EMAIL      you@example.com
ADMIN_PASSWORD   a-strong-password
```

The bootstrap is deliberately conservative, because it runs unattended on every
deploy:

- It does nothing unless **both** variables are set, so a deploy cannot mint an
  account with a blank password.
- It does nothing once any admin exists, so a redeploy never creates a second
  account and **never resets an existing password**.
- It never resets the password of a user who already signed up with that email
  through the UI; it only promotes them to admin.
- Passwords under 8 characters, and malformed addresses, are refused with a log
  line instead of creating a broken account.

After signing in and changing the password, **delete `ADMIN_PASSWORD`** from the
platform's dashboard so the credential is no longer stored. `ADMIN_EMAIL` can
stay.

### Migrations on deploy

`wsgi.py` runs `flask db upgrade` in a daemon thread at process start, so no
separate migration step is needed on platforms without a pre-deploy hook. If
you prefer an explicit step, run `flask db upgrade` in your release command and
it is a no-op afterwards.

The chain is safe to apply to an empty database: the initial migration was
re-baselined and `tests/test_migrations.py` asserts the migrations produce
exactly the model schema, so a fresh server and a `create_all()` server are
identical.

---

## Platform notes

### gunicorn is Linux-only

The `Procfile` and `Dockerfile` both use gunicorn, which **cannot run on
Windows** (`ModuleNotFoundError: No module named 'fcntl'`). This is fine for
Render, Heroku, Fly, Railway and Docker — all Linux. For local Windows
development use `python run.py`, or `waitress` for a production-like server.

### Render / Heroku / Fly

`Procfile` is picked up automatically. Health check path is `/health`. Note
that Render's free tier spins down when idle and its filesystem is ephemeral, so
`UPLOAD_DIR` must point at a mounted disk or uploads will not persist.

### Docker

```bash
docker compose up -d
```

Compose starts `postgres:16-alpine` behind a healthcheck so the web container
waits for `initdb` before its startup migration runs.

### Behind a TLS-terminating proxy

`ProxyFix` is already applied (`x_for=1, x_proto=1, x_host=1, x_prefix=1`).
Without it, `FORCE_HTTPS` causes an infinite redirect loop. The app trusts
exactly one proxy hop — if you have two (e.g. CDN + load balancer) you must
raise those counts or `X-Forwarded-Proto` will be ignored.

---

## Backups before you take traffic

```bash
python scripts/backup_db.py --retention 30
```

Custom-format `pg_dump` archives. **Not scheduled by default** — wire it to cron
or Task Scheduler before launch, and test a restore. See
[`BACKUP.md`](BACKUP.md).

---

## Known gaps

These are not bugs, but they are not finished either. Decide before launch.

1. **Payments are not integrated.** `initialize_payment` is a scaffold: it sets
   the record to "ready for a provider" and flashes a placeholder. No provider
   is wired up, so orders cannot actually be paid. An admin can still mark a
   payment paid manually.
2. **Single gunicorn worker.** `--workers 1 --threads 8` in the `Procfile` and
   `Dockerfile`. One slow request blocks the whole app, and there is no
   redundancy. Before real traffic, raise workers and confirm
   `workers × DB_POOL_SIZE` stays under PostgreSQL's `max_connections`.

---

## Post-deploy checklist

- [ ] `GET /health` returns `"status": "healthy"` and the server version
- [ ] Admin can sign in at `/auth/login` and reach `/admin`
- [ ] List a car, upload a photo, place an order, cancel it — money must show
      two decimal places everywhere
- [ ] Restart the service and confirm sessions survive (proves `SECRET_KEY` is
      stable)
- [ ] Upload a photo, restart, confirm the image is still there (proves
      `UPLOAD_DIR` is persistent)
- [ ] A scheduled backup ran and a restore into a scratch database succeeded
- [ ] HTTPS redirect and HSTS are active
