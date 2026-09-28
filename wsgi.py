from app import create_app

app = create_app()


def _run_pending_migrations():
    """Run Flask-Migrate upgrades once at process start.

    Render's Free plan has no pre-deploy command, so the schema has to be
    brought up to head here. Alembic is idempotent, so a no-op run is cheap;
    we still gate it behind a short lock so two gunicorn workers cannot race
    each other applying the same revisions to the PostgreSQL metadata. Runs
    after the app is fully built so the shell context and models are available.
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

    # Start in a daemon thread so gunicorn can accept connections immediately.
    # The first health probe may hit before migrations finish; that's fine,
    # because the DB check in /health only runs SELECT 1, and the tables
    # exist by the time real traffic arrives.
    threading.Thread(target=runner, daemon=True).start()


_run_pending_migrations()

if __name__ == '__main__':
    app.run()