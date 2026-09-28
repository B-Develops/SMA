from app import db, bcrypt
from datetime import datetime
from decimal import Decimal
from flask_login import UserMixin

# Money is stored as NUMERIC(14, 2) in PostgreSQL. A double-precision column
# cannot represent kobo exactly, so summing order amounts drifts by fractions
# of a naira; NUMERIC is exact and is the only sane type for currency in PG.
MONEY = db.Numeric(14, 2, asdecimal=True)

# Status/flag columns carry both a Python-side default (for ORM inserts) and a
# server_default (for raw-SQL inserts). cars/routes.py inserts listings with a
# text() statement that omits `status`, and without the server default those
# rows would land with status = NULL and disappear from every filtered query.


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        db.CheckConstraint("failed_login_attempts >= 0", name="ck_users_failed_login_attempts"),
    )
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    role = db.Column(db.String(20), nullable=False, server_default="user", default='user', index=True)
    avatar_url = db.Column(db.String(256), nullable=True)
    email_verified = db.Column(db.Integer, nullable=False, server_default="0", default=0)
    phone_verified = db.Column(db.Integer, nullable=False, server_default="0", default=0)
    id_verified = db.Column(db.Integer, nullable=False, server_default="0", default=0)
    address_verified = db.Column(db.Integer, nullable=False, server_default="0", default=0)
    # Security fields for login tracking
    failed_login_attempts = db.Column(db.Integer, nullable=False, server_default="0", default=0)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    email_verification_token = db.Column(db.String(128), nullable=True)
    email_verification_token_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        """Hash a password with bcrypt.

        bcrypt is the single hashing scheme used across the app: signup, login,
        password reset and the profile password change all use Flask-Bcrypt's
        generate/check pair, because they are the only paths a real user takes.
        These helpers previously used Werkzeug, whose default is scrypt. A
        scrypt hash cannot be verified by Flask-Bcrypt, so any account created
        through set_password -- the admin CLI and the startup bootstrap --
        produced a hash that login rejected with ValueError: Invalid salt, a
        500 rather than a failed login.
        """
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def get_verification_percentage(self):
        verified_count = sum([
            self.email_verified,
            self.phone_verified,
            self.id_verified,
            self.address_verified
        ])
        return (verified_count / 4) * 100


class Car(db.Model):
    __tablename__ = 'cars'
    __table_args__ = (
        db.CheckConstraint("year IS NULL OR year BETWEEN 1900 AND 2100", name="ck_cars_year"),
        db.CheckConstraint("price >= 0", name="ck_cars_price_non_negative"),
    )
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    make = db.Column(db.String(50), nullable=False, index=True)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer)
    price = db.Column(MONEY, nullable=False, index=True)
    mileage = db.Column(db.Integer)
    transmission = db.Column(db.String(20))
    condition = db.Column(db.String(20))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(256))
    status = db.Column(db.String(20), nullable=False, server_default="active", default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    seller = db.relationship('User', backref='cars')


class Order(db.Model):
    __tablename__ = 'orders'
    __table_args__ = (
        db.CheckConstraint("order_amount >= 0", name="ck_orders_amount_non_negative"),
        db.CheckConstraint("listed_price >= 0", name="ck_orders_listed_price_non_negative"),
        # The dashboard counts pending/confirmed per buyer on every page load.
        db.Index("ix_orders_buyer_status", "buyer_id", "status"),
    )
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False, index=True)
    order_amount = db.Column(MONEY, nullable=False)
    listed_price = db.Column(MONEY, nullable=False)
    status = db.Column(db.String(20), nullable=False, server_default="pending", default='pending', index=True)
    payment_method = db.Column(db.String(50))
    delivery_address = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)

    car = db.relationship('Car', backref=db.backref('orders', lazy=True))
    payments = db.relationship('Payment', backref='order', lazy=True, cascade='all, delete-orphan')

    @property
    def latest_payment(self):
        return self.payments[-1] if self.payments else None


class Payment(db.Model):
    __tablename__ = 'payments'
    __table_args__ = (
        db.CheckConstraint("amount >= 0", name="ck_payments_amount_non_negative"),
    )
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False, index=True)
    amount = db.Column(MONEY, nullable=False)
    currency = db.Column(db.String(3), nullable=False, server_default="NGN", default='NGN')
    provider = db.Column(db.String(50), nullable=False, server_default="unset", default='unset')
    provider_reference = db.Column(db.String(120), unique=True, nullable=True, index=True)
    status = db.Column(db.String(30), nullable=False, server_default="pending", default='pending', index=True)
    payment_data = db.Column(db.Text, nullable=True)
    receipt_url = db.Column(db.String(256), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    failed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SavedCar(db.Model):
    __tablename__ = 'saved_cars'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'car_id', name='unique_user_car'),)


class Notification(db.Model):
    __tablename__ = 'notifications'
    __table_args__ = (
        db.Index("ix_notifications_user_is_read", "user_id", "is_read"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(256))
    is_read = db.Column(db.Integer, nullable=False, server_default="0", default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NotificationSettings(db.Model):
    __tablename__ = 'notification_settings'
    __table_args__ = (
        db.UniqueConstraint("user_id", name="uq_notification_settings_user_id"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email_order_notifications = db.Column(db.Integer, nullable=False, server_default="1", default=1)
    email_message_notifications = db.Column(db.Integer, nullable=False, server_default="1", default=1)
    email_order_accepted = db.Column(db.Integer, nullable=False, server_default="1", default=1)
    email_price_drop = db.Column(db.Integer, nullable=False, server_default="1", default=1)
    push_new_orders = db.Column(db.Integer, nullable=False, server_default="1", default=1)
    push_messages = db.Column(db.Integer, nullable=False, server_default="1", default=1)
    push_order_accepted = db.Column(db.Integer, nullable=False, server_default="1", default=1)
    in_app_notifications = db.Column(db.Integer, nullable=False, server_default="1", default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Integer, nullable=False, server_default="0", default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='password_reset_tokens')


class AdminActionLog(db.Model):
    __tablename__ = "admin_action_logs"
    __table_args__ = (
        db.Index("ix_admin_action_logs_admin_created", "admin_id", "created_at"),
    )
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(50), nullable=False)       # delete_user, delete_listing, cancel_order …
    resource_type = db.Column(db.String(50), nullable=False) # User, Car, Order, …
    resource_id = db.Column(db.Integer, nullable=True)       # FK value of affected row
    details = db.Column(db.Text, nullable=True)              # free-form JSON or string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("User", backref="admin_actions")
