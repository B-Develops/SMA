# Implementation Priority List - Sarkin Mota Autos

## 🚨 CRITICAL (Fix Before ANY Launch)

### 1. Add CSRF Protection to All Forms

**Why:** Prevents Cross-Site Request Forgery attacks - major security vulnerability  
**Effort:** 2 hours  
**Files affected:** All templates with `<form>` tags  
**Steps:**

1. `pip install Flask-WTF`
2. Add to app.py: `from flask_wtf import CSRFProtect` and `csrf = CSRFProtect(app)`
3. Add `{{ csrf_token() }}` to every form in templates

---

### 2. Fix Route Protection Bug (/cars/list issue)

**Why:** Currently prevents regular users from listing cars - breaks core feature  
**Effort:** 10 minutes  
**Files:** app.py lines ~850-900  
**Fix:** Remove `@admin_required` from `/cars/list` and `/cars/my-listings` routes

```python
@app.route("/cars/list", methods=["GET", "POST"])
@login_required  # ✅ Keep this
# @admin_required  # ❌ Remove this line!
def list_car():
```

---

### 3. Add Error Pages (404, 500, 403)

**Why:** Default Flask errors expose version info and look bad  
**Effort:** 1 hour  
**Create:**

- `templates/errors/404.html`
- `templates/errors/500.html`
- `templates/errors/403.html`

**Add to app.py:**

```python
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403
```

---

### 4. Add Security Headers

**Why:** Protects against XSS, clickjacking, MIME-sniffing attacks  
**Effort:** 30 minutes  
**Add to app.py:**

```python
@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response
```

---

## 🔴 HIGH PRIORITY (Do This Week)

### 5. Implement Messages/Chat System

**Why:** Core marketplace feature - users can't contact sellers  
**Effort:** 8-10 hours  
**Need:**

1. Add Message model to app.py
2. Create `/messages` routes (list, view, send, delete)
3. Create `/messages/<int:user_id>` for conversation view
4. Update Messages.html template
5. Add message indicators to UI

**Key Routes:**

```python
@app.route("/messages")  # List conversations
@app.route("/messages/<int:user_id>")  # View conversation
@app.route("/messages/<int:user_id>/send", methods=["POST"])  # Send message
@app.route("/messages/<int:msg_id>/delete", methods=["POST"])  # Delete message
```

---

### 6. Complete Notification System

**Why:** Users don't know when things happen (orders received, accepted, etc.)  
**Effort:** 6-8 hours  
**Missing:**

1. Create notification when order placed (seller gets notified)
2. Create notification when order accepted (buyer gets notified)
3. Create notification when order rejected (buyer gets notified)
4. Send email notifications (optional but recommended)

**Where to add:**

```python
# In place_order() function after order created:
create_notification(
    seller.id,
    'order_received',
    f'New Order: {car.year} {car.make}',
    f'{buyer.name} offered ₦{order_amount:,.0f}',
    f'/admin/orders/{order.id}'
)

# In admin_accept_order():
create_notification(
    order.buyer_id,
    'order_accepted',
    'Your Order Was Accepted!',
    f'Seller accepted your ₦{order.order_amount:,.0f} offer',
    f'/orders/{order_id}/success'
)
```

---

### 7. Add Rate Limiting

**Why:** Prevents brute force attacks on login  
**Effort:** 1-2 hours  
**Steps:**

1. `pip install Flask-Limiter`
2. Initialize in app.py
3. Add `@limiter.limit()` to login and signup routes

```python
from flask_limiter import Limiter
limiter = Limiter(app=app, key_func=get_remote_address)

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    # existing code
```

---

### 8. Implement Payment Integration

**Why:** No revenue collection - **BIGGEST BLOCKER**  
**Effort:** 12-16 hours  
**Options:**

- Stripe (best international)
- Paystack (Nigeria-focused, recommended)
- Flutterwave (Nigeria-focused)

**Minimal Implementation:**

1. Add `payment_status` column to orders table
2. Create checkout route
3. Integrate payment SDK
4. Update order status on success
5. Send payment confirmation email

**Key Routes:**

```python
@app.route("/checkout/<int:order_id>")
@app.route("/payment/callback", methods=["POST"])
@app.route("/payment/webhook", methods=["POST"])
```

---

## 🟡 MEDIUM PRIORITY (Do This Month)

### 9. Email Verification on Signup

**Why:** Prevents spam/fake accounts  
**Effort:** 4-5 hours  
**Steps:**

1. Generate verification token (use secrets module)
2. Send verification email
3. Create `/verify/<token>` route
4. Block orders until verified

---

### 10. Password Reset System

**Why:** Users can't recover lost passwords  
**Effort:** 3-4 hours  
**Routes needed:**

- `/forgot-password` - form for email
- `/reset/<token>` - form to set new password
- Email with reset link

---

### 11. Seller Verification Workflow

**Why:** Prevents fraudulent sellers from listing  
**Effort:** 8-10 hours  
**Need:**

1. Mark new sellers as "unverified"
2. Admin approval system
3. Verification badges on listings
4. Block unverified sellers from listing (or flag listings)

---

### 12. Review & Rating System

**Why:** Builds trust, shows seller quality  
**Effort:** 8-10 hours  
**Need:**

1. Add Review model
2. Allow buyers to review sellers after order
3. Calculate average rating
4. Display on seller profile
5. Filter by rating on browse page

---

### 13. Public Seller Profiles

**Why:** Buyers want to see seller history before buying  
**Effort:** 4-5 hours  
**Need:**

- `/sellers/<seller_id>` route
- Show seller info, listings, ratings, reviews
- Response time stats
- Contact seller button

---

### 14. Complete Notifications UI

**Why:** Notification bell should show count and dropdown  
**Effort:** 3-4 hours  
**Need:**

1. Add notification badge to navbar
2. Create notification dropdown preview
3. Real-time notification using WebSockets (or polling)
4. Mark as read on click

---

## 📋 NICE TO HAVE

### 15. Email Notification Preferences

- Route exists, needs settings persistence
- Send emails based on user preferences

### 16. Search History / Recent Searches

- Store user searches
- Show suggestions

### 17. Wishlist Features

- Advanced saved searches
- Price drop alerts

### 18. Admin Analytics Dashboard

- Revenue charts
- User growth
- Order success rate
- Top sellers

### 19. Two-Factor Authentication (2FA)

- Optional security feature
- Low priority

### 20. Mobile Responsiveness

- Many templates need mobile testing

---

## QUICK WINS (Do These First - High Impact, Low Effort)

1. **Fix /cars/list route** - 10 min, enables core feature
2. **Add error pages** - 1 hour, huge UX improvement
3. **Add CSRF tokens** - 2 hours, critical security
4. **Add security headers** - 30 min, security hardening
5. **Fix admin_required issues** - 10 min, enables features

**Combined effort:** ~4 hours for massive improvements

---

## ESTIMATED EFFORT SUMMARY

| Category           | Items  | Est. Hours | Priority      |
| ------------------ | ------ | ---------- | ------------- |
| Critical Security  | 4      | 5-6        | 🚨 Now        |
| Core Features      | 3      | 20-25      | 🔴 This Week  |
| Trust/Verification | 3      | 15-20      | 🟡 This Month |
| Nice to Have       | 7      | 30+        | 📋 Later      |
| **TOTAL**          | **17** | **70-75**  | -             |

**For 1 developer:** ~3 weeks full-time to complete all critical + high items

---

## RECOMMENDED EXECUTION ORDER

### Week 1 (Security & Core Fixes):

1. Fix /cars/list route (10 min)
2. Add CSRF protection (2 hrs)
3. Add error pages (1 hr)
4. Add security headers (30 min)
5. Add rate limiting (2 hrs)
   → **~5.5 hours** - Website is more secure and functional

### Week 1-2 (Core Features):

6. Implement messages system (10 hrs)
7. Complete notifications (6 hrs)
   → **~16 hours** - Basic marketplace communication works

### Week 2-3 (Revenue):

8. Payment integration (14 hrs)
   → **~14 hours** - Can collect money from orders

### Week 3+ (Trust & Polish):

9. Email verification (4 hrs)
10. Seller verification (8 hrs)
11. Review system (8 hrs)
    → **~20 hours** - Platform is trustworthy

---

## TESTING CHECKLIST (After Each Feature)

- [ ] Feature works in dev environment
- [ ] No console errors
- [ ] Mobile responsive
- [ ] Database changes migrated
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Proper error handling
- [ ] User feedback (flash messages)

---

_Last Updated: May 19, 2026_
