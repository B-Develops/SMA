import os
import secrets
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_caching import Cache
from flask_migrate import Migrate
from datetime import timedelta, datetime
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from .monitoring import setup_production_logging, RequestLoggingMiddleware, metrics

# Initialize extensions (but do not bind to app yet)
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
mail = Mail()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
)
migrate = Migrate()
talisman = Talisman(
    force_https=os.environ.get("FORCE_HTTPS", "False") == "True",
    strict_transport_security=os.environ.get("HSTS", "False") == "True",
    frame_options='SAMEORIGIN',
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", "data:", "https:"],
        'font-src': ["'self'"],
    }
)

cache = Cache()

import rq

def _get_or_create_secret_key():
    key_file = Path(__file__).parent.parent.parent / ".secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    key_file.write_text(key)
    return key


def get_time_ago(time_diff):
    """Convert a timedelta object to a human-readable 'time ago' string."""
    total_seconds = int(time_diff.total_seconds())
    
    if total_seconds < 60:
        return "just now"
    elif total_seconds < 3600:  # Less than 1 hour
        minutes = total_seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif total_seconds < 86400:  # Less than 1 day
        hours = total_seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif total_seconds < 172800:  # Less than 2 days
        return "yesterday"
    elif total_seconds < 604800:  # Less than 1 week
        days = total_seconds // 86400
        return f"{days} days ago"
    else:
        weeks = total_seconds // 604800
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"

def create_app(config_name=None):
    """Application factory function."""
    app = Flask(__name__)
    
    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or _get_or_create_secret_key()
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", 
        "sqlite:///database.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    engine_options = {"pool_pre_ping": True, "pool_recycle": 3600}
    db_url = app.config["SQLALCHEMY_DATABASE_URI"]
    if db_url and not db_url.startswith("sqlite"):
        engine_options.update({
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
        })
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_SIZE_MB", 16)) * 1024 * 1024  # Configurable via env, default 16 MB
    
    # Security configurations
    app.config["PERMANENT_SESSION_LIFETIME"] = int(os.environ.get("SESSION_TIMEOUT_MINUTES", 30)) * 60  # Convert to seconds
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "True") != "False"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_DURATION"] = int(os.environ.get("SESSION_TIMEOUT_MINUTES", 30)) * 60
    app.config["REMEMBER_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "True") != "False"
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
    
    # Email Configuration
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", True)
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@sarkinmotaautos.com")
    app.config["TESTING"] = os.environ.get("FLASK_ENV") == "testing"
    
    # Base URL for email templates and redirects
    app.config["BASE_URL"] = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
    
    # Cache configuration
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        app.config["CACHE_TYPE"] = "redis"
        app.config["CACHE_REDIS_URL"] = redis_url
        app.config["CACHE_DEFAULT_TIMEOUT"] = 300
    else:
        app.config["CACHE_TYPE"] = "simple"
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)

    setup_production_logging(app)
    app.wsgi_app = RequestLoggingMiddleware(app.wsgi_app)

    # Register Jinja2 date filter
    def format_date(dt, fmt='Y-m-d'):
        """Format datetime object to string."""
        if not dt:
            return 'N/A'
        if isinstance(dt, datetime):
            # Handle different format strings
            if fmt == 'Y-m-d':
                return dt.strftime('%Y-%m-%d')
            elif fmt == 'Y-m-d H:i:s':
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return dt.strftime(fmt)
        return str(dt)
    
    def format_currency(value):
        return f"₦{value:,.2f}"

    app.jinja_env.filters['date'] = format_date
    app.jinja_env.filters['currency'] = format_currency
    
    # Import models to ensure they are registered
    from .models import User
    
    # Configure Flask-Login
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_unread_notifications():
        from flask_login import current_user
        try:
            if current_user and getattr(current_user, 'is_authenticated', False):
                from .models import Notification
                count = Notification.query.filter_by(user_id=current_user.id, is_read=0).count()
            else:
                count = 0
        except Exception:
            count = 0
        return dict(unread_notifications=count)
    
    # Register blueprints
    from .blueprints.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from .blueprints.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from .blueprints.cars import cars_bp
    app.register_blueprint(cars_bp, url_prefix='/cars')
    
    from .blueprints.orders import orders_bp
    app.register_blueprint(orders_bp, url_prefix='/orders')
    
    from .blueprints.payments import payments_bp
    app.register_blueprint(payments_bp, url_prefix='')
    
    from .blueprints.profiles import profiles_bp
    app.register_blueprint(profiles_bp, url_prefix='')
    
    from .blueprints.mobile import mobile_bp
    app.register_blueprint(mobile_bp, url_prefix='/mobile')
    
    # Landing page route
    @app.route("/")
    def index():
        return render_template("Index.html")
    
    # User dashboard route
    @app.route("/dashboard")
    @login_required
    def dashboard():
        from .models import Order, SavedCar, Car
        from datetime import datetime, timedelta
        
        # Calculate user stats
        pending_orders = Order.query.filter_by(buyer_id=current_user.id, status='pending').count()
        confirmed_orders = Order.query.filter_by(buyer_id=current_user.id, status='confirmed').count()
        
        # Get recent orders for dashboard table (show all, not just pending/confirmed)
        from sqlalchemy.orm import joinedload
        
        active_orders = Order.query.options(joinedload(Order.car))\
            .filter_by(buyer_id=current_user.id)\
            .order_by(Order.created_at.desc()).limit(5).all()
        
        # Get saved cars
        saved_cars = db.session.query(Car).join(SavedCar).filter(SavedCar.user_id == current_user.id).all()
        
        # Generate activity timeline
        activities = []
        
        # Get recent orders (last 10) with cars eager-loaded
        from sqlalchemy.orm import joinedload
        recent_orders = Order.query.options(joinedload(Order.car))\
            .filter_by(buyer_id=current_user.id)\
            .order_by(Order.created_at.desc()).limit(10).all()
        for order in recent_orders:
            car = order.car
            if car:
                time_diff = datetime.utcnow() - order.created_at
                time_str = get_time_ago(time_diff)
                activities.append({
                    'type': 'order',
                    'title': f"You ordered {car.year} {car.make} {car.model}",
                    'time': time_str,
                    'icon': 'shopping-cart',
                    'timestamp': order.created_at
                })
        
        # Get recent saved cars (last 10)
        recent_saves = db.session.query(SavedCar, Car).join(Car).filter(SavedCar.user_id == current_user.id).order_by(SavedCar.created_at.desc()).limit(10).all()
        for save, car in recent_saves:
            time_diff = datetime.utcnow() - save.created_at
            time_str = get_time_ago(time_diff)
            activities.append({
                'type': 'save',
                'title': f"You saved {car.year} {car.make} {car.model}",
                'time': time_str,
                'icon': 'heart',
                'timestamp': save.created_at
            })
        
        # Get user's approved listings (if seller)
        user_listings = Car.query.filter_by(seller_id=current_user.id, status='active').order_by(Car.created_at.desc()).limit(5).all()
        for listing in user_listings:
            time_diff = datetime.utcnow() - listing.created_at
            time_str = get_time_ago(time_diff)
            activities.append({
                'type': 'listing',
                'title': f"Your {listing.year} {listing.make} {listing.model} was approved",
                'time': time_str,
                'icon': 'check-circle',
                'timestamp': listing.created_at
            })
        
        # Sort activities by timestamp (newest first) and limit to 5
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        activities = activities[:5]

        from .models import Notification
        notifications_preview = Notification.query.filter_by(user_id=current_user.id)
        notifications_preview = notifications_preview.order_by(Notification.created_at.desc()).limit(3).all()
        
        stats = {
            'active_orders': pending_orders + confirmed_orders,
            'saved_cars': SavedCar.query.filter_by(user_id=current_user.id).count(),
            'purchased_cars': Order.query.filter_by(buyer_id=current_user.id, status='completed').count(),
            'notifications': Notification.query.filter_by(user_id=current_user.id, is_read=0).count()
        }
        
        unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=0).count()
        
        return render_template(
            "dashboard.html",
            stats=stats,
            watchlist=saved_cars,
            activities=activities,
            orders=active_orders,
            notifications=notifications_preview,
            unread_notifications=unread_notifications,
            is_admin=current_user.role == 'admin'
        )
    
    # Health check endpoint
    @app.route("/health")
    def health_check():
        """Health check endpoint for monitoring systems."""
        from sqlalchemy import text
        from datetime import datetime
        import json
        status = {"status": "healthy", "checks": {}, "timestamp": datetime.utcnow().isoformat()}
        overall_code = 200

        db_latency_ms = 0
        db_start = time.perf_counter()
        try:
            db.session.execute(text("SELECT 1"))
            db_latency_ms = round((time.perf_counter() - db_start) * 1000, 2)
            status["checks"]["database"] = {"status": "connected", "latency_ms": db_latency_ms}
            metrics.gauge("health.db.latency_ms", db_latency_ms)
        except Exception as e:
            status["checks"]["database"] = {"status": "error", "error": str(e)}
            status["status"] = "degraded"
            overall_code = 503
            metrics.alert("critical", "Database health check failed", {"error": str(e)})

        try:
            import redis
            r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
            r.ping()
            status["checks"]["cache"] = {"status": "connected"}
        except Exception:
            status["checks"]["cache"] = {"status": "unavailable"}
            if status["status"] == "healthy":
                status["status"] = "degraded"
                overall_code = 503

        metrics.gauge("health.status", 1 if status["status"] == "healthy" else 0)

        return json.dumps(status), overall_code, {'Content-Type': 'application/json'}

    @app.route("/metrics")
    def metrics_endpoint():
        """Prometheus-style metrics endpoint."""
        summary = metrics.get_summary()
        lines = []
        for name, value in summary["counters"].items():
            lines.append(f"sarkinmota_{name} {value}")
        for name, data in summary["timings"].items():
            lines.append(f"sarkinmota_{name}_count {data['count']}")
            lines.append(f"sarkinmota_{name}_avg_ms {data['avg_ms']}")
            lines.append(f"sarkinmota_{name}_p95_ms {data['p95_ms']}")
        for name, value in summary["gauges"].items():
            lines.append(f"sarkinmota_{name} {value}")
        return "\n".join(lines), 200, {'Content-Type': 'text/plain'}
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return (
            render_template("errors/400.html"),
            400,
        )

    @app.errorhandler(403)
    def forbidden(e):
        return (
            render_template("errors/403.html"),
            403,
        )

    @app.errorhandler(404)
    def not_found(e):
        return (
            render_template("errors/404.html"),
            404,
        )

    @app.errorhandler(500)
    def internal_error(e):
        return (
            render_template("errors/500.html"),
            500,
        )

    @app.errorhandler(503)
    def service_unavailable(e):
        return (
            render_template("errors/503.html"),
            503,
        )

    # Shell context for flask cli
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db}

    return app
