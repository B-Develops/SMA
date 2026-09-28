from app import create_app

app = create_app()


def _startup_tasks():
    """Bring the database up to head, then create the first admin if configured.

    Render's Free plan has no pre-deploy command and no shell, so both the
    schema and the initial admin have to be handled here at process start.

    Alembic is idempotent, so a no-op run is cheap; the lock stops two
    gunicorn workers racing on the same PostgreSQL metadata. The admin
    bootstrap must run after the migration, since it queries the users table,
    so the two share a single thread to guarantee ordering.

    Runs after the app is fully built so the shell context and models are
    available.
    """
    import threading

    lock = threading.Lock()

    def runner():
        with lock:
            try:
                from flask_migrate import upgrade
                with app.app_context():
                    upgrade()
                app.logger.info("Database migrations applied at startup.")
            except Exception as exc:  # pragma: no cover - defensive
                app.logger.error("Startup migration failed: %s", exc)
                return

            try:
                from app.bootstrap import bootstrap_admin_from_env
                # The app is passed explicitly: this runs on a bare thread with
                # no application context, so current_app is not usable.
                bootstrap_admin_from_env(app)
            except Exception as exc:  # pragma: no cover - defensive
                app.logger.error("Admin bootstrap failed: %s", exc)

    # Start in a daemon thread so gunicorn can accept connections immediately.
    # The first health probe may hit before migrations finish; that's fine,
    # because the DB check in /health only runs SELECT 1, and the tables
    # exist by the time real traffic arrives.
    threading.Thread(target=runner, daemon=True).start()


_startup_tasks()

if __name__ == '__main__':
    app.run()