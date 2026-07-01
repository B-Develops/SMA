# PRODUCTION READINESS ACTION PLAN

**Target:** Production launch in 6-8 weeks  
**Team:** 2-3 engineers recommended  
**Budget:** $5,000-$15,000 (infrastructure + tools)

---

## PHASE 1: SECURITY HARDENING (Week 1) - CRITICAL

### Sprint 1.1: CSRF & Error Handling (2 days)

**Task 1.1.1: Enable CSRF Protection** (2 hours)

- [ ] Verify Flask-WTF is installed (in requirements.txt ✅)
- [ ] Add CSRF token to ALL form templates:
  - `app/templates/auth/Sign-up.html`
  - `app/templates/login.html`
  - `app/templates/dashboard/ListCars.html`
  - `app/templates/dashboard/EditCar.html`
  - All other form pages
- [ ] Test with curl that CSRF protection blocks requests without token
- [ ] Documentation: Add CSRF requirement to contributing guide

**Template Pattern:**

```html
<form method="POST">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />
  <!-- form fields -->
</form>
```

**Task 1.1.2: Create Custom Error Handlers** (1 hour)

- [ ] Create `app/templates/errors/404.html`
- [ ] Create `app/templates/errors/500.html`
- [ ] Create `app/templates/errors/403.html`
- [ ] Register handlers in `app/__init__.py`:

  ```python
  @app.errorhandler(404)
  def not_found(e):
      return render_template('errors/404.html'), 404

  @app.errorhandler(500)
  def server_error(e):
      app.logger.error(f'Server error: {e}')
      return render_template('errors/500.html'), 500
  ```

- [ ] Test error pages manually (navigate to /nonexistent)

---

### Sprint 1.2: Logging & Monitoring Setup (2 days)

**Task 1.2.1: Implement Centralized Logging** (2 hours)

- [ ] Create `app/logging_config.py`:

  ```python
  import logging
  from logging.handlers import RotatingFileHandler
  import os

  def setup_logging(app):
      if not app.debug:
          if not os.path.exists('logs'):
              os.mkdir('logs')
          file_handler = RotatingFileHandler('logs/sarkin_mota.log',
                                            maxBytes=10000000,
                                            backupCount=10)
          file_handler.setFormatter(logging.Formatter(
              '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
          ))
          file_handler.setLevel(logging.INFO)
          app.logger.addHandler(file_handler)
          app.logger.setLevel(logging.INFO)
          app.logger.info('Sarkin Mota Autos startup')
  ```

- [ ] Call setup_logging in `app/__init__.py`
- [ ] Log key events:
  - User registration
  - User login (success/failure)
  - Failed login attempts
  - Admin actions
  - Errors/exceptions
- [ ] Test by triggering errors and checking logs/

**Task 1.2.2: Set Up Error Monitoring** (1 hour)

- [ ] Sign up for Sentry (free tier available)
- [ ] Install sentry-sdk: `pip install sentry-sdk`
- [ ] Integrate with Flask:

  ```python
  import sentry_sdk
  from sentry_sdk.integrations.flask import FlaskIntegration

  sentry_sdk.init(
      dsn=os.environ.get('SENTRY_DSN'),
      integrations=[FlaskIntegration()]
  )
  ```

- [ ] Add SENTRY_DSN to .env
- [ ] Test by triggering an error and verifying it appears in Sentry

---

### Sprint 1.3: Secret Management (1 day)

**Task 1.3.1: Secure SECRET_KEY Management** (1 hour)

- [ ] Update `app/__init__.py` to fail in production if SECRET_KEY not set:
  ```python
  app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
  if not app.config["SECRET_KEY"]:
      if os.environ.get("FLASK_ENV") == "production":
          raise ValueError("SECRET_KEY must be set in production")
      else:
          app.config["SECRET_KEY"] = "dev-secret-key-UNSAFE"
  ```
- [ ] Generate production secret key: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Create `.env.example` file (for developers)
- [ ] Update `.gitignore` to exclude `.env`
- [ ] Document in README how to set environment variables

---

### Sprint 1.4: File Upload Security (1 day)

**Task 1.4.1: Secure File Upload Endpoint** (3 hours)

- [ ] Move uploads outside web root (if possible)
- [ ] Create protected upload endpoint:
  ```python
  @app.route('/uploads/<path:filename>')
  @login_required
  def serve_upload(filename):
      """Serve uploaded files with access control"""
      # Verify user owns this file
      car = Car.query.filter_by(image_url=f"uploads/{filename}").first()
      if not car:
          abort(404)
      # Only allow seller or admins to view
      if current_user.id != car.seller_id and current_user.role != 'admin':
          abort(403)
      return send_from_directory(UPLOAD_FOLDER, filename)
  ```
- [ ] Update all image references to use new protected endpoint
- [ ] Test permission checks (non-owner can't access)

**Task 1.4.2: Update File Upload Validation** (1 hour)

- [ ] Keep existing MIME type validation ✅
- [ ] Add file size validation:
  ```python
  MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
  if file.size > MAX_UPLOAD_SIZE:
      return error
  ```
- [ ] Verify python-magic is installed for MIME checking

---

### Sprint 1.5: Password Security (1 day)

**Task 1.5.1: Fix Hardcoded Secret Key** (30 min)

- [ ] Ensure production environment has SECRET_KEY set
- [ ] Test in both development and production modes

**Task 1.5.2: Add Password Reset** (4 hours)

- [ ] Create password reset route in `app/blueprints/auth/routes.py`:

  ```python
  @auth_bp.route('/forgot-password', methods=['GET', 'POST'])
  def forgot_password():
      if request.method == 'POST':
          email = request.form.get('email')
          user = User.query.filter_by(email=email).first()

          if user:
              # Generate reset token
              reset_token = secrets.token_urlsafe(32)
              user.reset_password_token = reset_token
              user.reset_password_token_expires = datetime.utcnow() + timedelta(hours=1)
              db.session.commit()

              # Send reset email
              send_password_reset_email(user.email, reset_token)
              flash('Password reset link sent to your email', 'success')
          else:
              flash('Email not found', 'info')  # Generic message

          return redirect(url_for('auth.login'))

      return render_template('auth/ForgotPassword.html')

  @auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
  def reset_password(token):
      user = User.query.filter_by(reset_password_token=token).first()

      if not user or user.reset_password_token_expires < datetime.utcnow():
          flash('Invalid or expired token', 'error')
          return redirect(url_for('auth.login'))

      if request.method == 'POST':
          password = request.form.get('password')
          # Validate password
          user.password = bcrypt.generate_password_hash(password).decode('utf-8')
          user.reset_password_token = None
          user.reset_password_token_expires = None
          db.session.commit()

          flash('Password reset successfully. Please log in.', 'success')
          return redirect(url_for('auth.login'))

      return render_template('auth/ResetPassword.html')
  ```

- [ ] Create templates: `auth/ForgotPassword.html`, `auth/ResetPassword.html`
- [ ] Update User model to add reset_password_token fields
- [ ] Send password reset emails (already have email infrastructure)

---

**Week 1 Deliverables:**

- [ ] CSRF protection enabled
- [ ] Error handlers created
- [ ] Logging system operational
- [ ] Sentry error tracking active
- [ ] SECRET_KEY properly secured
- [ ] File upload security improved
- [ ] Password reset functionality working

**Week 1 Testing:**

- [ ] Verify CSRF blocks requests without token
- [ ] Verify errors logged to file
- [ ] Verify Sentry captures errors
- [ ] Verify password reset email works
- [ ] Manual security review

---

## PHASE 2: CORE FEATURES (Week 2)

### Sprint 2.1: Messaging System (3 days)

**Task 2.1.1: Create Message Model** (1 hour)

- [ ] Add Message model to `app/models.py`:
  ```python
  class Message(db.Model):
      __tablename__ = 'messages'
      id = db.Column(db.Integer, primary_key=True)
      sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
      recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
      car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=True)
      subject = db.Column(db.String(200), nullable=False)
      body = db.Column(db.Text, nullable=False)
      is_read = db.Column(db.Boolean, default=False)
      created_at = db.Column(db.DateTime, default=datetime.utcnow)

      sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
      recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
      car = db.relationship('Car')
  ```
- [ ] Run migration to create table

**Task 2.1.2: Create Messaging Routes** (3 hours)

- [ ] Create `app/blueprints/messages/__init__.py` and `routes.py`
- [ ] Implement routes:
  - GET `/messages` — list conversations
  - GET `/messages/<int:user_id>` — view conversation with user
  - POST `/messages/send` — send message
  - PATCH `/messages/<int:id>/mark-read` — mark as read
  - POST `/messages/<int:id>/delete` — soft delete message

**Task 2.1.3: Create Messaging Templates** (2 hours)

- [ ] Create `templates/Messaging.html` — main messaging page
- [ ] Create `templates/Conversation.html` — individual conversation
- [ ] Add messaging link to dashboard
- [ ] Add message count badge to navigation

**Task 2.1.4: Add Notifications** (2 hours)

- [ ] Send email when message received (if user preference set)
- [ ] Add in-app notification badge (red dot on messages icon)
- [ ] Create notification center for message previews

---

### Sprint 2.2: Payment Integration (2 days)

**Task 2.2.1: Choose Payment Provider** (30 min)

- [ ] Options for Nigeria:
  - Paystack (recommended - simplest)
  - Flutterwave
  - PagSeguro
- [ ] Recommendation: **Paystack** (easiest integration)
- [ ] Sign up for Paystack sandbox account
- [ ] Get API keys

**Task 2.2.2: Implement Paystack Integration** (4 hours)

- [ ] Install `pip install requests`
- [ ] Create payment service in `app/services/payment_service.py`:

  ```python
  import requests

  class PaystackService:
      def __init__(self, secret_key):
          self.secret_key = secret_key
          self.base_url = "https://api.paystack.co"

      def initialize_transaction(self, amount_naira, email, reference):
          """Initialize payment transaction"""
          headers = {
              "Authorization": f"Bearer {self.secret_key}",
              "Content-Type": "application/json"
          }
          data = {
              "amount": int(amount_naira * 100),  # Convert to kobo
              "email": email,
              "reference": reference
          }
          response = requests.post(f"{self.base_url}/transaction/initialize",
                                  json=data, headers=headers)
          return response.json()

      def verify_transaction(self, reference):
          """Verify payment was successful"""
          headers = {"Authorization": f"Bearer {self.secret_key}"}
          response = requests.get(f"{self.base_url}/transaction/verify/{reference}",
                                 headers=headers)
          return response.json()
  ```

- [ ] Create payment route in `app/blueprints/orders/routes.py`:

  ```python
  @orders_bp.route('/<int:order_id>/pay', methods=['POST'])
  @login_required
  def pay_for_order(order_id):
      order = Order.query.get(order_id)
      if order.buyer_id != current_user.id:
          abort(403)

      # Initialize payment
      payment_service = PaystackService(os.environ.get('PAYSTACK_SECRET_KEY'))
      result = payment_service.initialize_transaction(
          amount_naira=order.order_amount,
          email=current_user.email,
          reference=f"order-{order_id}"
      )

      # Redirect to Paystack payment page
      return redirect(result['data']['authorization_url'])

  @orders_bp.route('/payment-callback')
  def payment_callback():
      reference = request.args.get('reference')

      payment_service = PaystackService(os.environ.get('PAYSTACK_SECRET_KEY'))
      result = payment_service.verify_transaction(reference)

      if result['status'] and result['data']['status'] == 'success':
          order_id = int(result['data']['reference'].split('-')[1])
          order = Order.query.get(order_id)
          order.status = 'confirmed'
          db.session.commit()
          flash('Payment successful!', 'success')
          return redirect(url_for('orders.my_orders'))

      flash('Payment failed', 'error')
      return redirect(url_for('orders.my_orders'))
  ```

- [ ] Add PAYSTACK_SECRET_KEY to .env
- [ ] Test with Paystack sandbox

---

### Sprint 2.3: Seller Verification (2 days)

**Task 2.3.1: Create Verification Model** (1 hour)

- [ ] Add SellerVerification model:
  ```python
  class SellerVerification(db.Model):
      __tablename__ = 'seller_verifications'
      id = db.Column(db.Integer, primary_key=True)
      seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
      phone_verified = db.Column(db.Boolean, default=False)
      email_verified = db.Column(db.Boolean, default=False)
      id_verified = db.Column(db.Boolean, default=False)
      business_verified = db.Column(db.Boolean, default=False)
      verification_score = db.Column(db.Integer, default=0)  # 0-100
      verified_at = db.Column(db.DateTime, nullable=True)
      created_at = db.Column(db.DateTime, default=datetime.utcnow)

      seller = db.relationship('User', backref='verification')
  ```

**Task 2.3.2: Create Verification Routes** (3 hours)

- [ ] Create verification dashboard
- [ ] Routes:
  - GET `/seller/verification` — verification status
  - POST `/seller/verify-phone` — verify phone OTP
  - POST `/seller/verify-id` — upload government ID
  - GET `/seller/verification-score` — show verification %
- [ ] Add verification badge to seller profiles

**Task 2.3.3: Implement Phone Verification** (2 hours)

- [ ] Use Termii or Twilio for SMS OTP
- [ ] Send OTP on request
- [ ] Verify OTP code
- [ ] Mark phone as verified

---

**Week 2 Deliverables:**

- [ ] Messaging system functional
- [ ] Payment integration (Paystack) working
- [ ] Seller verification system in place
- [ ] Phone verification working

**Week 2 Testing:**

- [ ] Send test message and verify it arrives
- [ ] Complete test payment (sandbox mode)
- [ ] Verify seller badge appears
- [ ] Verify OTP SMS sends and validates

---

## PHASE 3: INFRASTRUCTURE & SCALING (Week 3)

### Sprint 3.1: Database Migration (2 days)

**Task 3.1.1: Set Up PostgreSQL** (2 hours)

- [ ] Install PostgreSQL locally for testing
- [ ] Create new database: `createdb sarkin_mota_production`
- [ ] Update requirements.txt: add `psycopg2-binary`
- [ ] Install: `pip install psycopg2-binary`

**Task 3.1.2: Migrate Data** (2 hours)

- [ ] Export SQLite data
- [ ] Import to PostgreSQL
- [ ] Verify all data transferred correctly
- [ ] Create backup of original SQLite DB

**Task 3.1.3: Update Database Connection** (1 hour)

- [ ] Update `app/__init__.py`:
  ```python
  app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
      "DATABASE_URL",
      "postgresql://user:password@localhost/sarkin_mota_production"
  )
  ```
- [ ] Test connection with both local PostgreSQL and cloud (Heroku/Railway)

---

### Sprint 3.2: Caching Layer (Redis) (1 day)

**Task 3.2.1: Set Up Redis** (2 hours)

- [ ] Install Redis locally (or use Docker)
- [ ] Install Python client: `pip install redis flask-caching`
- [ ] Configure Redis in app:

  ```python
  from flask_caching import Cache

  cache = Cache(app, config={'CACHE_TYPE': 'redis',
                             'CACHE_REDIS_URL': os.environ.get('REDIS_URL')})
  ```

**Task 3.2.2: Cache Frequent Queries** (2 hours)

- [ ] Cache car listings: `@cache.cached(timeout=300)` (5 minutes)
- [ ] Cache user profiles: `@cache.cached(timeout=600)` (10 minutes)
- [ ] Cache admin statistics: `@cache.cached(timeout=3600)` (1 hour)
- [ ] Add cache invalidation on updates

---

### Sprint 3.3: Database Optimization (1 day)

**Task 3.3.1: Add Indexes** (1 hour)

- [ ] Add to `app/models.py` or migration:
  ```python
  db.Index('ix_users_email', User.email)
  db.Index('ix_cars_seller_id', Car.seller_id)
  db.Index('ix_cars_status', Car.status)
  db.Index('ix_orders_buyer_id', Order.buyer_id)
  db.Index('ix_orders_status', Order.status)
  db.Index('ix_saved_cars_user_id', SavedCar.user_id)
  ```

**Task 3.3.2: Query Optimization** (2 hours)

- [ ] Fix N+1 queries (use joinedload)
- [ ] Test query performance
- [ ] Monitor with django-silk or similar

---

### Sprint 3.4: Monitoring & Logging (1 day)

**Task 3.4.1: Set Up Datadog/New Relic** (2 hours)

- [ ] Sign up for free tier
- [ ] Install monitoring agent
- [ ] Track key metrics:
  - Request latency
  - Error rates
  - Database query time
  - Memory usage
  - CPU usage

**Task 3.4.2: Create Monitoring Dashboard** (1 hour)

- [ ] Dashboard with key metrics
- [ ] Alerts for high error rates
- [ ] Alerts for slow queries
- [ ] Daily health check email

---

**Week 3 Deliverables:**

- [ ] PostgreSQL migration complete
- [ ] Redis caching active
- [ ] Database indexes added
- [ ] Monitoring/logging operational
- [ ] Performance metrics baseline established

---

## PHASE 4: TESTING & QA (Week 4)

### Sprint 4.1: Integration Tests (3 days)

**Task 4.1.1: Write Authentication Tests** (2 hours)

- [ ] Test signup flow
- [ ] Test login/logout
- [ ] Test email verification
- [ ] Test password reset
- [ ] Test 2FA (when added)

**Task 4.1.2: Write Order Tests** (2 hours)

- [ ] Test order creation
- [ ] Test order cancellation
- [ ] Test payment flow (sandbox)
- [ ] Test order status updates

**Task 4.1.3: Write Messaging Tests** (2 hours)

- [ ] Test message sending
- [ ] Test message retrieval
- [ ] Test read/unread
- [ ] Test permissions

**Task 4.1.4: Write Car Listing Tests** (2 hours)

- [ ] Test listing creation
- [ ] Test listing editing
- [ ] Test listing deletion
- [ ] Test image upload

---

### Sprint 4.2: Security Testing (2 days)

**Task 4.2.1: Manual Security Review** (4 hours)

- [ ] CSRF attack attempts (should fail)
- [ ] SQLi attempts (should fail)
- [ ] XSS attempts (should fail)
- [ ] Unauthorized access attempts (should fail)
- [ ] Rate limiting verification

**Task 4.2.2: Penetration Testing** (4 hours)

- [ ] Consider hiring professional pentest ($2,000-5,000)
- [ ] Or use automated tools:
  - OWASP ZAP
  - Burp Suite Community
  - SQLMap
  - W3AF

---

### Sprint 4.3: Load Testing (2 days)

**Task 4.3.1: Set Up Load Testing** (2 hours)

- [ ] Use Apache JMeter or Locust
- [ ] Create test scenarios:
  - 100 concurrent users browsing
  - 10 concurrent users making orders
  - 5 concurrent users uploading images

**Task 4.3.2: Run Load Tests** (2 hours)

- [ ] Test with SQLite (baseline)
- [ ] Test with PostgreSQL + Redis
- [ ] Identify bottlenecks
- [ ] Document results

**Task 4.3.3: Performance Optimization** (4 hours)

- [ ] Fix identified bottlenecks
- [ ] Retest and verify improvements
- [ ] Document optimization results

---

### Sprint 4.4: Final QA (2 days)

**Task 4.4.1: Cross-Browser Testing** (2 hours)

- [ ] Test on Chrome, Firefox, Safari, Edge
- [ ] Test on mobile (iPhone, Android)
- [ ] Verify responsive design

**Task 4.4.2: Accessibility Audit** (2 hours)

- [ ] Run axe DevTools
- [ ] Fix flagged issues
- [ ] Test keyboard navigation
- [ ] Verify screen reader compatibility

**Task 4.4.3: UAT** (2 hours)

- [ ] Have actual users test
- [ ] Gather feedback
- [ ] Fix critical issues

---

**Week 4 Deliverables:**

- [ ] 50+ integration tests written
- [ ] Security audit passed
- [ ] Load testing completed
- [ ] Performance optimized
- [ ] UAT feedback incorporated

---

## LAUNCH PREPARATION (Week 5)

### Pre-Launch Checklist

**48 Hours Before Launch:**

- [ ] Final backup of database
- [ ] Final backup of code
- [ ] Staging environment mirrors production
- [ ] All team members briefed
- [ ] Rollback plan documented

**24 Hours Before Launch:**

- [ ] Final security review
- [ ] All tests passing
- [ ] Monitoring configured
- [ ] On-call schedule set
- [ ] Communication plan ready

**Launch Day (Early Morning):**

- [ ] Deploy to production
- [ ] Verify all systems operational
- [ ] Monitor error rates (first 2 hours critical)
- [ ] Have team standing by for issues
- [ ] Announce go-live

**Post-Launch (First Week):**

- [ ] Daily monitoring
- [ ] Quick fixes for any issues
- [ ] Monitor user feedback
- [ ] Performance tracking
- [ ] Plan v1.1 improvements

---

## RESOURCE REQUIREMENTS

### Team

- 1 Backend Engineer (Django/Flask expert)
- 1 Frontend Engineer (React/HTML/CSS)
- 1 DevOps Engineer (Database/Deployment)
- Optional: QA Engineer (Testing)

### Infrastructure Costs (Monthly)

- Database (PostgreSQL): $50-100
- Caching (Redis): $15-30
- File Storage (S3): $10-25
- Email Service: $0-50
- Monitoring (Datadog): $20-50
- Hosting (if self-hosted): $50-200
- **Total: $145-455/month**

### Development Tools

- Git (free)
- Sentry (free tier or $29/month)
- Postman (free)
- Load testing tool (free)
- **Total: $0-50/month**

---

## SUCCESS METRICS

### Technical

- Uptime: ≥ 99.5%
- Response time p95: < 500ms
- Error rate: < 0.1%
- Database query time p95: < 100ms
- Test coverage: ≥ 60%

### Business

- Users: 50-100 in first week
- Listings: 20-50 active cars
- Orders: 5-10 per week
- Conversion rate: ≥ 1%
- Customer satisfaction: ≥ 4/5 stars

### Security

- Vulnerabilities: 0 critical
- Failed login attempts logged: 100%
- Admin actions logged: 100%
- Data backups: Daily

---

## NEXT STEPS

1. **Today:** Review this plan with team
2. **Tomorrow:** Create Jira tickets for each task
3. **This Week:** Start Phase 1 (security fixes)
4. **Next Week:** Move to Phase 2 (features)
5. **Week 3:** Phase 3 (infrastructure)
6. **Week 4:** Phase 4 (testing)
7. **Week 5:** Launch preparation

---

**Estimated Total Effort:** 200 hours (≈ 6 weeks @ 40 hrs/week for 1 engineer)

With 2-3 engineers working in parallel: **4-6 weeks total**

Good luck! 🚀
