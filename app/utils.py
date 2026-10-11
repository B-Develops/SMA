from flask import render_template, current_app, request, url_for
from . import mail
from flask_mail import Message
import os
import logging
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

# Emit each misconfiguration warning at most once per process, so a
# per-request helper cannot flood the logs.
_warned_base_url = set()


def get_base_url():
    """The configured BASE_URL, used to build absolute links in emails.

    Verification and password-reset links are only useful if they point at the
    host that is actually serving the site. Render assigns a suffix to service
    names (sarkinmota becomes sarkinmota-842i), so a hand-written BASE_URL is
    easy to get wrong, and the failure is silent: emails still send, they just
    lead to a dead domain.

    The configured value stays authoritative rather than being derived from the
    request, because a spoofed Host or X-Forwarded-Host header would otherwise
    let an attacker choose the host embedded in outgoing mail, which is a
    ready-made phishing vector. A mismatch is logged instead.
    """
    configured = (current_app.config.get("BASE_URL") or "http://127.0.0.1:5000").rstrip("/")

    try:
        serving_host = request.host
    except RuntimeError:
        # No request context, e.g. a send from a background thread. There is
        # nothing to compare against, and nothing to do about it either way.
        return configured

    configured_host = urlsplit(configured).netloc
    if configured_host and serving_host and configured_host != serving_host:
        key = (configured_host, serving_host)
        if key not in _warned_base_url:
            _warned_base_url.add(key)
            logger.warning(
                "BASE_URL is %r but the request is being served by %r. Every "
                "verification and password-reset email will link to the wrong "
                "host. Set BASE_URL to https://%s in the platform's environment.",
                configured_host, serving_host, serving_host,
            )
    return configured


def _send_verification_email_direct(user_email, user_name, token):
    try:
        subject = "Verify your email - Sarkin Mota Autos"
        base_url = get_base_url()
        verification_url = f"{base_url}{url_for('auth.verify_email', token=token)}"

        html_body = render_template(
            'email/verification.html',
            user_name=user_name,
            verification_url=verification_url,
            base_url=base_url
        )

        if current_app.config.get("TESTING") or not current_app.config.get("MAIL_USERNAME"):
            logger.info("EMAIL WOULD BE SENT TO: %s | SUBJECT: %s", user_email, subject)
            logger.debug("EMAIL BODY:\n%s", html_body)
            return True

        msg = Message(
            subject=subject,
            recipients=[user_email],
            html=html_body
        )
        mail.send(msg)
        return True
    except Exception as e:
        logger.error("Error sending verification email: %s", str(e))
        return False


def _send_order_confirmation_email_direct(user_email, user_name, order_id, car, order_amount):
    try:
        subject = f"Order Confirmed - Sarkin Mota Autos (Order #{order_id})"
        base_url = get_base_url()

        html_body = render_template(
            'email/order_confirmation.html',
            user_name=user_name,
            order_id=order_id,
            car=car,
            order_amount=order_amount,
            base_url=base_url
        )

        if current_app.config.get("TESTING") or not current_app.config.get("MAIL_USERNAME"):
            logger.info("EMAIL WOULD BE SENT TO: %s | SUBJECT: %s", user_email, subject)
            logger.debug("EMAIL BODY:\n%s", html_body)
            return True

        msg = Message(
            subject=subject,
            recipients=[user_email],
            html=html_body
        )
        mail.send(msg)
        return True
    except Exception as e:
        logger.error("Error sending email: %s", str(e))
        return False


def _send_verification_email_job(user_email, user_name, token):
    from app import create_app
    app = create_app()
    with app.app_context():
        _send_verification_email_direct(user_email, user_name, token)


def _send_order_confirmation_email_job(user_email, user_name, order_id, car, order_amount):
    from app import create_app
    app = create_app()
    with app.app_context():
        _send_order_confirmation_email_direct(user_email, user_name, order_id, car, order_amount)


def send_verification_email(user_email, user_name, token):
    from app import create_app
    app = create_app()
    with app.app_context():
        if hasattr(app, 'rq_queue') and app.rq_queue:
            app.rq_queue.enqueue(_send_verification_email_job, user_email, user_name, token)
        else:
            _send_verification_email_direct(user_email, user_name, token)


def send_order_confirmation_email(user_email, user_name, order_id, car, order_amount):
    from app import create_app
    app = create_app()
    with app.app_context():
        if hasattr(app, 'rq_queue') and app.rq_queue:
            app.rq_queue.enqueue(_send_order_confirmation_email_job, user_email, user_name, order_id, car, order_amount)
        else:
            _send_order_confirmation_email_direct(user_email, user_name, order_id, car, order_amount)


def _send_password_reset_email_direct(user_email, user_name, token, base_url):
    try:
        subject = "Reset your password - Sarkin Mota Autos"
        # Built with url_for so the blueprint prefix cannot drift away from the
        # link in the email. This was hardcoded as /reset-password/<token>,
        # but the route is /auth/reset-password/<token>, so every reset email
        # led to a 404.
        reset_url = f"{base_url}{url_for('auth.reset_password', token=token)}"

        html_body = render_template(
            'email/password_reset.html',
            user_name=user_name,
            reset_url=reset_url,
            base_url=base_url
        )

        if current_app.config.get("TESTING") or not current_app.config.get("MAIL_USERNAME"):
            logger.info("EMAIL WOULD BE SENT TO: %s | SUBJECT: %s", user_email, subject)
            logger.debug("EMAIL BODY:\n%s", html_body)
            return True

        msg = Message(
            subject=subject,
            recipients=[user_email],
            html=html_body
        )
        mail.send(msg)
        return True
    except Exception as e:
        logger.error("Error sending password reset email: %s", str(e))
        return False


def _send_password_reset_email_job(user_email, user_name, token, base_url):
    from app import create_app
    app = create_app()
    with app.app_context():
        _send_password_reset_email_direct(user_email, user_name, token, base_url)


def send_password_reset_email(user_email, user_name, token, base_url):
    from app import create_app
    app = create_app()
    with app.app_context():
        if hasattr(app, 'rq_queue') and app.rq_queue:
            app.rq_queue.enqueue(_send_password_reset_email_job, user_email, user_name, token, base_url)
        else:
            _send_password_reset_email_direct(user_email, user_name, token, base_url)


def create_order_notification(user_id, order_id, event_type, title, message, link=None, actor_id=None, channel='in_app', metadata=None):
    """Create an in-app notification for a user related to an order.

    Returns the created Notification object.
    """
    from . import db
    from .models import Notification, NotificationSettings

    if not link:
        link = f"/orders/{order_id}"

    settings = NotificationSettings.query.filter_by(user_id=user_id).first()
    if settings and settings.in_app_notifications == 0 and channel == 'in_app':
        return None

    notif = Notification(
        user_id=user_id,
        type=event_type,
        title=title,
        message=message,
        link=link,
        is_read=0
    )
    try:
        db.session.add(notif)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # Respect user preference for email notifications (simple check)
    try:
        if settings and settings.email_order_notifications and channel in ('in_app', 'email'):
            # For now only send order confirmation emails for the buyer when appropriate
            # More advanced email templates can be added later.
            pass
    except Exception:
        # Don't let notification delivery failures break the flow
        pass

    return notif