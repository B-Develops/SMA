from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    role = db.Column(db.String(20), default='user')
    email_verified = db.Column(db.Integer, default=0)
    phone_verified = db.Column(db.Integer, default=0)
    id_verified = db.Column(db.Integer, default=0)
    address_verified = db.Column(db.Integer, default=0)
    # Security fields for login tracking
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime, nullable=True)
    email_verification_token = db.Column(db.String(128), nullable=True)
    email_verification_token_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

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
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer)
    price = db.Column(db.Float, nullable=False)
    mileage = db.Column(db.Integer)
    transmission = db.Column(db.String(20))
    condition = db.Column(db.String(20))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(256))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    seller = db.relationship('User', backref='cars')


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    order_amount = db.Column(db.Float, nullable=False)
    listed_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))
    delivery_address = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='NGN', nullable=False)
    provider = db.Column(db.String(50), default='unset', nullable=False)
    provider_reference = db.Column(db.String(120), unique=True, nullable=True, index=True)
    status = db.Column(db.String(30), default='pending', nullable=False, index=True)
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
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(256))
    is_read = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NotificationSettings(db.Model):
    __tablename__ = 'notification_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    email_order_notifications = db.Column(db.Integer, default=1)
    email_message_notifications = db.Column(db.Integer, default=1)
    email_order_accepted = db.Column(db.Integer, default=1)
    email_price_drop = db.Column(db.Integer, default=1)
    push_new_orders = db.Column(db.Integer, default=1)
    push_messages = db.Column(db.Integer, default=1)
    push_order_accepted = db.Column(db.Integer, default=1)
    in_app_notifications = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='password_reset_tokens')


class AdminActionLog(db.Model):
    __tablename__ = "admin_action_logs"
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(50), nullable=False)       # delete_user, delete_listing, cancel_order …
    resource_type = db.Column(db.String(50), nullable=False) # User, Car, Order, …
    resource_id = db.Column(db.Integer, nullable=True)       # FK value of affected row
    details = db.Column(db.Text, nullable=True)              # free-form JSON or string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship("User", backref="admin_actions")