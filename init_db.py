"""Create the PostgreSQL schema and stamp the Alembic chain.

``db.create_all()`` builds the tables straight from the models, and
``stamp()`` then records the chain as already applied so that future
``flask db upgrade`` runs start from the current head instead of replaying
history onto tables that already exist.

``flask db upgrade`` alone is the other valid entry point -- the initial
migration is now re-baselined and can create the base tables from zero.
"""
import os
import sys

from app import create_app, db, bcrypt
from app.models import (
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


def main():
    app = create_app()

    with app.app_context():
        engine = db.engine
        if engine.dialect.name != "postgresql":
            raise SystemExit(
                f"Refusing to initialise: expected PostgreSQL, got "
                f"{engine.dialect.name!r}. Check DATABASE_URL in your .env file."
            )

        print(f"PostgreSQL: {engine.url.render_as_string(hide_password=True)}")
        print(f"Server version: {engine.dialect.server_version_info}")

        db.create_all()
        print("Tables created/verified.")

        try:
            from flask_migrate import stamp

            stamp()
            print("Migration chain stamped to head.")
        except Exception as exc:  # pragma: no cover - stamp is advisory here
            print(f"Could not stamp migrations ({exc}). Run 'flask db stamp head' manually.")

        if os.environ.get("CREATE_TEST_USER", "False") == "True":
            existing_user = User.query.filter_by(email="test@example.com").first()
            if not existing_user:
                hashed_password = bcrypt.generate_password_hash("password123").decode("utf-8")
                db.session.add(User(email="test@example.com", password=hashed_password))
                db.session.commit()
                print("Test user created: test@example.com / password123")
            else:
                print("Test user already exists")
        else:
            print("Skipping test user creation (set CREATE_TEST_USER=True to enable)")


if __name__ == "__main__":
    sys.exit(main())
