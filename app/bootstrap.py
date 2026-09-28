"""First-run admin bootstrap.

Render's free tier has no shell, so `flask create-admin` cannot be run on a
fresh deployment. Instead, an admin can be created from environment variables
the first time the app boots.

Safety properties, because this runs unattended on every deploy:

* Both ADMIN_EMAIL and ADMIN_PASSWORD must be set, so a deploy cannot
  accidentally mint an account with a blank password.
* It is a no-op once any admin exists, so a redeploy never creates a second
  one and never resets an existing password.
* The password is only ever read from the environment, never logged, and
  never persisted in plaintext.

Unset ADMIN_PASSWORD once the account exists, so the credential is no longer
retained by the platform.
"""
import logging
import os

from app import db
from app.models import User

logger = logging.getLogger("sarkinmota.bootstrap")

MIN_PASSWORD_LENGTH = 8


def bootstrap_admin_from_env(app=None):
    """Create the first admin from ADMIN_EMAIL / ADMIN_PASSWORD if none exists.

    Returns the admin's email when an account was created, otherwise None.
    Safe to call on every process start.

    ``app`` may be passed when there is no active application context. Without
    it the function relies on ``current_app``, which raises when called from a
    bare startup thread -- exactly where wsgi.py calls it from.
    """
    email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD") or ""

    if not email or not password:
        return None

    if "@" not in email:
        logger.error("ADMIN_EMAIL is not a valid address; skipping bootstrap.")
        return None

    if len(password) < MIN_PASSWORD_LENGTH:
        logger.error(
            "ADMIN_PASSWORD is shorter than %d characters; skipping bootstrap.",
            MIN_PASSWORD_LENGTH,
        )
        return None

    if app is None:
        from flask import current_app

        app = current_app._get_current_object()

    with app.app_context():
        if User.query.filter_by(role="admin").first() is not None:
            logger.info("An admin already exists; skipping bootstrap.")
            return None

        # A user may already have signed up with this address through the UI.
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email, name="Administrator", email_verified=1)
        user.role = "admin"
        if not user.password:
            user.set_password(password)
        db.session.add(user)
        db.session.commit()

        logger.warning(
            "Bootstrapped the first admin account (%s). Unset ADMIN_PASSWORD now "
            "that it exists.", email,
        )
        return email
