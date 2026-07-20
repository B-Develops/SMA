from flask import render_template, current_app
from . import mail
from flask_mail import Message
import os
import logging

logger = logging.getLogger(__name__)


def _send_verification_email_direct(user_email, user_name, token):
    try:
        subject = "Verify your email - Sarkin Mota Autos"
        base_url = current_app.config.get("BASE_URL", "http://127.0.0.1:5000")
        verification_url = f"{base_url}/auth/verify-email/{token}"

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
        base_url = current_app.config.get("BASE_URL", "http://127.0.0.1:5000")

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
        reset_url = f"{base_url}/reset-password/{token}"

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