# Critical Security Fixes - Implementation Guide

## 1. Add Security Configuration & CSRF Protection

Add this to the top of `app.py` after imports:

```python
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from email_validator import validate_email, EmailNotValidError
import secrets

# Initialize security extensions
csrf = CSRFProtect(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Security Configuration
app.config["PERMANENT_SESSION_LIFETIME"] = 30 * 60  # 30 minutes
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Ensure SECRET_KEY is never the debug key in production
if app.config.get("SECRET_KEY") == "dev-secret-key-change-in-production":
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError("CRITICAL: SECRET_KEY not set in production!")
    print("⚠️  WARNING: Using development SECRET_KEY")
```

---

## 2. Add Security Headers

Add this after creating the Flask app:

```python
@app.after_request
def set_security_headers(response):
    """Add security headers to every response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    # Content Security Policy - strict
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "  # Can be 'unsafe-inline' if you can't modify JS
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'"
    )
    
    return response
```

---

## 3. Fix Admin Route Protection

**BEFORE** (app.py line ~950):
```python
@app.route("/cars/list", methods=["GET", "POST"])
@login_required
@admin_required  # WRONG - blocks regular users from listing cars!
def list_car():
```

**AFTER**:
```python
@app.route("/cars/list", methods=["GET", "POST"])
@login_required  # Keep this, remove @admin_required
def list_car():
```

---

## 4. Add Comprehensive Input Validation

Replace the signup route (around line 347):

```python
@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle user registration with proper validation."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate required fields
        if not name or not email or not password:
            flash("All fields are required", "error")
            return redirect(url_for("signup"))

        # Validate name (no special characters)
        if not name.replace(" ", "").isalnum():
            flash("Name contains invalid characters", "error")
            return redirect(url_for("signup"))

        # Validate email format
        try:
            validate_email(email)
        except EmailNotValidError:
            flash("Invalid email address", "error")
            return redirect(url_for("signup"))

        # Validate password strength
        if len(password) < 12:
            flash("Password must be at least 12 characters long", "error")
            return redirect(url_for("signup"))
        
        if not any(c.isupper() for c in password):
            flash("Password must contain uppercase letters", "error")
            return redirect(url_for("signup"))
        
        if not any(c.isdigit() for c in password):
            flash("Password must contain numbers", "error")
            return redirect(url_for("signup"))

        # Validate passwords match
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("signup"))

        # Check if email already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered", "error")
            return redirect(url_for("signup"))
        
        # Hash password and create user
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(email=email, password=hashed_password, name=name)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("auth/Sign-up.html")
```

---

## 5. Add Rate Limiting to Login

Add `@limiter.limit()` decorator to login route:

**BEFORE** (line ~330):
```python
@app.route("/login", methods=["GET", "POST"])
def login():
```

**AFTER**:
```python
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")  # Max 5 login attempts per minute
def login():
```

Similarly for signup:
```python
@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("3 per hour")  # Max 3 registration attempts per hour
def signup():
```

---

## 6. Add CSRF Tokens to Forms (In Templates)

Every `<form>` needs a CSRF token. Update all forms in HTML templates:

```html
<form method="POST" action="/login">
    {{ csrf_token() }}
    <!-- rest of form -->
</form>
```

Or if using Jinja2:
```html
<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- rest of form -->
</form>
```

---

## 7. Improve File Upload Security

Replace `save_uploaded_image()` function:

```python
import magic  # from python-magic package

def save_uploaded_image(file, car_id):
    """
    Process and save uploaded car image with security validation.
    """
    if not file or file.filename == "":
        return None
    
    if not allowed_file(file.filename):
        return None
    
    # Validate MIME type (magic bytes)
    file.seek(0)
    file_content = file.read()
    file.seek(0)
    
    # Check MIME type using magic bytes
    mime = magic.Magic(mime=True)
    detected_mime = mime.from_buffer(file_content)
    
    allowed_mimes = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
    if detected_mime not in allowed_mimes:
        return None  # Silently reject invalid MIME types
    
    # Validate file size (prevent bombs)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per image
    if len(file_content) > MAX_FILE_SIZE:
        return None
    
    # Generate unique filename
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"car_{car_id}_{secrets.token_hex(8)}.{ext}"
    
    # Save file
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as f:
        f.write(file_content)
    
    return f"uploads/{filename}"
```

---

## 8. Add Authorization Checks

Add this helper function:

```python
def check_ownership(item_id, item_type='car'):
    """Check if current user owns the specified item."""
    if item_type == 'car':
        car = Car.query.get_or_404(item_id)
        if car.seller_id != current_user.id:
            abort(403)
        return car
    
    elif item_type == 'order':
        order = Order.query.get_or_404(item_id)
        if order.buyer_id != current_user.id:
            abort(403)
        return order
```

Use it before allowing user to modify their data:
```python
@app.route("/cars/<int:car_id>/edit", methods=["POST"])
@login_required
def edit_car(car_id):
    car = check_ownership(car_id, 'car')
    # Now safe to modify car
    ...
```

---

## 9. Add Error Handlers

```python
@app.errorhandler(403)
def forbidden(error):
    """Handle forbidden access."""
    return render_template("error.html", 
                          code=403, 
                          message="You don't have permission to access this."), 403

@app.errorhandler(404)
def not_found(error):
    """Handle page not found."""
    return render_template("error.html", 
                          code=404, 
                          message="Page not found."), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle server errors."""
    db.session.rollback()
    # Log error details
    app.logger.error(f'Server Error: {error}')
    return render_template("error.html", 
                          code=500, 
                          message="A server error occurred. Please try again later."), 500
```

---

## 10. Add Audit Logging

```python
from datetime import datetime

def log_action(user_id, action, details="", level="INFO"):
    """Log important actions for audit trail."""
    timestamp = datetime.utcnow()
    app.logger.log(
        getattr(logging, level),
        f"[AUDIT] User {user_id} | Action: {action} | Details: {details} | Time: {timestamp}"
    )

# Usage examples:
log_action(current_user.id, "LOGIN", f"IP: {request.remote_addr}")
log_action(current_user.id, "DELETE_LISTING", f"Car ID: {car_id}")
log_action(current_user.id, "ACCEPT_ORDER", f"Order ID: {order_id}")
```

---

## 11. Remove Hardcoded Debug Values

Search for and remove from templates:
- Debug query parameters
- Test email addresses
- Hardcoded user IDs
- API keys or tokens

---

## 12. Add .env Template

Create `.env.example` (commit to git):
```env
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=postgresql://user:password@localhost/dbname
MAX_CONTENT_LENGTH=16777216
SESSION_TIMEOUT_MINUTES=30
```

Create `.env` (add to .gitignore, never commit):
```env
# Copy from .env.example and fill in your values
```

---

## Testing These Changes

Run these tests after implementing:

```bash
# Test CSRF protection
curl -X POST http://localhost:5000/login  # Should fail without token

# Test rate limiting  
for i in {1..10}; do curl -X POST http://localhost:5000/login -d "email=test@test.com&password=wrong"; done
# After 5 attempts should return 429

# Test headers
curl -I http://localhost:5000 | grep -i "x-content-type-options"
```

