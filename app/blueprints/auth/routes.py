from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ...models import User, PasswordResetToken
from ... import db, bcrypt
from email_validator import validate_email, EmailNotValidError
import secrets
from datetime import datetime, timedelta
from ...utils import send_verification_email, send_order_confirmation_email, send_password_reset_email
from . import auth_bp

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration with username, email, and password."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name or not email or not password:
            flash('All fields are required', 'error')
            return redirect(url_for('auth.signup'))

        # Validate email format
        try:
            from flask import current_app
            check_deliv = not current_app.config.get('TESTING', False)
        except RuntimeError:
            check_deliv = False
        try:
            validated = validate_email(email, check_deliverability=check_deliv)
            email = validated.email
        except EmailNotValidError:
            if not check_deliv:
                email = email.strip().lower()
            else:
                flash('Invalid email address', 'error')
                return redirect(url_for('auth.signup'))

        # Check if email already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already registered', 'error')
            return redirect(url_for('auth.signup'))

        # Password complexity requirements
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return redirect(url_for('auth.signup'))

        if not any(c.isupper() for c in password):
            flash('Password must contain at least one uppercase letter', 'error')
            return redirect(url_for('auth.signup'))

        if not any(c.islower() for c in password):
            flash('Password must contain at least one lowercase letter', 'error')
            return redirect(url_for('auth.signup'))

        if not any(c.isdigit() for c in password):
            flash('Password must contain at least one digit', 'error')
            return redirect(url_for('auth.signup'))

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for c in password):
            flash('Password must contain at least one special character', 'error')
            return redirect(url_for('auth.signup'))

        # Hash password and create user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password=hashed_password, name=name)
        db.session.add(new_user)
        db.session.commit()

        # Generate email verification token
        verification_token = secrets.token_urlsafe(32)
        token_expires = datetime.utcnow() + timedelta(hours=1)

        # Update user with verification token
        new_user.email_verification_token = verification_token
        new_user.email_verification_token_expires = token_expires
        db.session.commit()

        # Send verification email
        send_verification_email(
            user_email=new_user.email,
            user_name=new_user.name,
            token=verification_token
        )

        flash('Account created successfully! Please check your email to verify your account.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/Sign-up.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_input = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email_input).first()

        # Check if account is locked due to too many failed attempts
        if user and hasattr(user, 'failed_login_attempts') and user.failed_login_attempts >= 5:
            lockout_time = datetime.utcnow() - timedelta(minutes=30)
            if user.last_failed_login and user.last_failed_login > lockout_time:
                flash('Account temporarily locked due to too many failed login attempts. Please try again later.', 'error')
                return redirect(url_for('auth.login'))
            else:
                # Reset failed attempts if lockout period has passed
                user.failed_login_attempts = 0
                db.session.commit()

        if user:
            if bcrypt.check_password_hash(user.password, password):
                # Check if email is verified
                if hasattr(user, 'email_verified') and user.email_verified == 0:
                    flash('Please verify your email address before logging in. Check your email for the verification link.', 'warning')
                    return redirect(url_for('auth.login'))

                login_user(user)
                # Reset failed login attempts on successful login
                if hasattr(user, 'failed_login_attempts'):
                    user.failed_login_attempts = 0
                    user.last_failed_login = None
                    db.session.commit()
                if user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                # Increment failed login attempts
                if not hasattr(user, 'failed_login_attempts'):
                    # Add columns if they don't exist (for migration safety)
                    try:
                        user.failed_login_attempts = 1
                        user.last_failed_login = datetime.utcnow()
                        db.session.commit()
                    except:
                        db.session.rollback()
                else:
                    user.failed_login_attempts += 1
                    user.last_failed_login = datetime.utcnow()
                    db.session.commit()

                remaining_attempts = 5 - user.failed_login_attempts
                if remaining_attempts > 0:
                    flash(f'Invalid email or password. {remaining_attempts} attempt(s) remaining before account lockout.', 'error')
                else:
                    flash('Account locked due to too many failed login attempts. Please try again later.', 'error')
                return redirect(url_for('auth.login'))

        # Even if user doesn't exist, show generic message to prevent user enumeration
        flash('Invalid email or password', 'error')
        return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify user's email address with token."""
    user = User.query.filter_by(email_verification_token=token).first()

    if not user:
        flash('Invalid verification link.', 'error')
        return redirect(url_for('auth.login'))

    # Check if token has expired
    if hasattr(user, 'email_verification_token_expires') and user.email_verification_token_expires:
        if user.email_verification_token_expires < datetime.utcnow():
            flash('Verification link has expired. Please request a new one.', 'error')
            return redirect(url_for('auth.login'))

    # Mark email as verified
    user.email_verified = 1
    user.email_verification_token = None
    user.email_verification_token_expires = None
    db.session.commit()

    flash('Email verified successfully! You can now log in.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/resend-verification')
@login_required
def resend_verification():
    """Resend email verification link."""
    if current_user.email_verified == 1:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('dashboard'))

    # Generate new verification token
    verification_token = secrets.token_urlsafe(32)
    token_expires = datetime.utcnow() + timedelta(hours=1)

    # Update user with verification token
    current_user.email_verification_token = verification_token
    current_user.email_verification_token_expires = token_expires
    db.session.commit()

    # Send verification email
    send_verification_email(
        user_email=current_user.email,
        user_name=current_user.name,
        token=verification_token
    )

    flash('Verification email has been resent!', 'success')
    return redirect(url_for('dashboard'))

@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password requests."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()

        if not email:
            flash('Please enter your email address.', 'error')
            return redirect(url_for('auth.forgot_password'))

        try:
            validated = validate_email(email, check_deliverability=False)
            email = validated.email
        except EmailNotValidError:
            email = email.strip().lower()

        user = User.query.filter_by(email=email).first()

        if not user:
            flash('If an account exists with that email, a reset link has been sent.', 'info')
            return redirect(url_for('auth.login'))

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        PasswordResetToken.query.filter_by(user_id=user.id, used=0).update({'used': 1})
        reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
        db.session.add(reset_token)
        db.session.commit()

        try:
            from flask import current_app
            base_url = current_app.config.get('BASE_URL', request.host_url.rstrip('/'))
        except RuntimeError:
            base_url = request.host_url.rstrip('/')

        send_password_reset_email(
            user_email=user.email,
            user_name=user.name or 'User',
            token=token,
            base_url=base_url
        )

        flash('If an account exists with that email, a reset link has been sent.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/ForgotPassword.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token."""
    reset_token = PasswordResetToken.query.filter_by(token=token, used=0).first()

    if not reset_token:
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('auth.login'))

    if reset_token.expires_at < datetime.utcnow():
        flash('This reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not password or not confirm_password:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        if not any(c.isupper() for c in password):
            flash('Password must contain at least one uppercase letter.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        if not any(c.islower() for c in password):
            flash('Password must contain at least one lowercase letter.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        if not any(c.isdigit() for c in password):
            flash('Password must contain at least one digit.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for c in password):
            flash('Password must contain at least one special character.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        user = User.query.get(reset_token.user_id)
        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        reset_token.used = 1
        db.session.commit()

        flash('Password reset successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/ResetPassword.html', token=token)