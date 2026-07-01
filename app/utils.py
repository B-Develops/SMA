from flask import render_template, current_app
from . import mail
from flask_mail import Message
import os

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
            print("\n" + "="*80)
            print(f"EMAIL WOULD BE SENT TO: {user_email}")
            print(f"SUBJECT: {subject}")
            print(f"FROM: {current_app.config.get('MAIL_DEFAULT_SENDER')}")
            print("="*80)
            print(html_body)
            print("="*80 + "\n")
            return True

        msg = Message(
            subject=subject,
            recipients=[user_email],
            html=html_body
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
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
            print("\n" + "="*80)
            print(f"EMAIL WOULD BE SENT TO: {user_email}")
            print(f"SUBJECT: {subject}")
            print(f"FROM: {current_app.config.get('MAIL_DEFAULT_SENDER')}")
            print("="*80)
            print(html_body)
            print("="*80 + "\n")
            return True

        msg = Message(
            subject=subject,
            recipients=[user_email],
            html=html_body
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
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