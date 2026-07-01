# Security & Production Hardening Guide

## Critical Issues (Fix Immediately)

### 1. **CSRF Protection Missing**
- **Risk**: Cross-Site Request Forgery attacks on form submissions
- **Impact**: Attackers can perform unauthorized actions (delete listings, accept orders, etc.)
- **Fix**: Add Flask-WTF for CSRF token generation and validation

### 2. **SQL Injection Vulnerabilities** 
- **Risk**: Raw SQL queries with user input (e.g., in dashboard route)
- **Example**: The `dashboard()` route uses raw SQL - vulnerable if parameter passed unsafely
- **Fix**: Use SQLAlchemy ORM exclusively, never raw SQL for dynamic queries

### 3. **Missing Input Validation**
- **Risk**: Malicious data stored in database
- **Issues**: 
  - Signup: No email format validation, weak password requirements
  - Car listing: No validation of year (could be negative or far future)
  - Order amount: No validation it's positive or reasonable
- **Fix**: Add comprehensive validation on all form inputs

### 4. **No Rate Limiting**
- **Risk**: Brute force attacks on login, spam uploads
- **Fix**: Add Flask-Limiter to rate-limit authentication endpoints

### 5. **Hardcoded Secret Key**
- **Risk**: Debug secret key is known to attackers
- **Issue**: `"dev-secret-key-change-in-production"` in app.py
- **Fix**: Ensure SECRET_KEY is ONLY set from environment variables in production

### 6. **Missing Security Headers**
- **Risk**: Clickjacking, MIME type sniffing, XSS attacks
- **Fix**: Add X-Frame-Options, X-Content-Type-Options, CSP headers

### 7. **Debug Mode Could Be On**
- **Risk**: Stack traces, environment variables exposed if debug=True
- **Fix**: Ensure `app.run(debug=False)` in production

### 8. **No Password Requirements**
- **Risk**: Users can set weak passwords
- **Fix**: Enforce minimum length (12+ chars), complexity requirements

---

## High Priority Issues

### 9. **Unprotected Admin Routes**
- **Issue**: `/cars/list` and `/cars/my-listings` require `@admin_required` - but regular users should list cars!
- **Risk**: Only admins can create listings
- **Fix**: Remove `@admin_required` from user listing routes

### 10. **No Authorization Checks on User Actions**
- **Issues**:
  - User can order same car multiple times
  - No verification user owns the car before editing
  - User data in `/admin/users` is exposed without pagination
- **Fix**: Add proper ownership checks before allow PUT/DELETE operations

### 11. **Sensitive Data Exposure**
- **Issues**: 
  - User's phone, location, email visible to anyone viewing orders
  - User list in admin dashboard shows all emails without access control details
- **Fix**: Sanitize sensitive fields from JSON responses, require proper authorization

### 12. **No Logging or Audit Trail**
- **Risk**: Can't trace unauthorized actions or security incidents
- **Fix**: Add Flask logging, log all sensitive actions (logins, admin changes, deletions)

### 13. **File Upload Vulnerabilities**
- **Issue**: While extension checking exists, need more validation
- **Risks**:
  - Executable code could be uploaded as image (MIME type validation missing)
  - No file size limit on POST body
  - Image path traversal possible
- **Fix**: 
  - Add MIME type validation (magic bytes check)
  - Scan files for malicious content
  - Validate file headers, not just extensions

### 14. **Missing Error Handling**
- **Issues**: Generic exception messages shown to users
- **Risks**: Stack traces might leak in production
- **Fix**: Implement proper error handler with generic messages to users, detailed logs to admins

### 15. **No Account Lockout**
- **Risk**: Unlimited password guess attempts
- **Fix**: Lock account after 5 failed attempts, require admin unlock

---

## Medium Priority Issues

### 16. **Weak Email Verification**
- **Issue**: Email verified flag exists but never enforced
- **Risk**: Users can register with fake emails
- **Fix**: Send verification email before account activation

### 17. **No HTTPS Enforcement**
- **Risk**: Credentials sent over plain HTTP
- **Fix**: 
  - Set `PREFERRED_URL_SCHEME = 'https'` in config
  - Add redirect from HTTP to HTTPS
  - Enable HSTS header

### 18. **Missing Request Size Limits**
- **Issue**: While MAX_CONTENT_LENGTH=16MB exists, could be bypassed
- **Fix**: Add more granular limits per endpoint type

### 19. **No XSS Protection on Templating**
- **Risk**: User-submitted descriptions not escaped in templates
- **Fix**: Use Jinja2's auto-escaping (should be on by default)
- **Verify**: All `{{ }}` in templates properly escape user input

### 20. **Database Backup & Recovery Issues**
- **Risk**: No automated backups shown
- **Fix**: Implement daily encrypted backups, test recovery procedures

### 21. **Weak Session Management**
- **Issue**: No session timeout configured
- **Fix**: Add `PERMANENT_SESSION_LIFETIME = 30 minutes` to config

### 22. **No API Rate Limiting**
- **Risk**: Endpoints like `/cars/<id>/order` can be spammed
- **Fix**: Rate limit all POST/DELETE endpoints

---

## Implementation Checklist

### Immediate (Before Production):
- [ ] Add Flask-WTF for CSRF protection
- [ ] Add Flask-Limiter for rate limiting
- [ ] Implement email validation on signup
- [ ] Add password complexity requirements (12+ chars, mixed case, numbers)
- [ ] Add security headers (X-Frame-Options, CSP, etc.)
- [ ] Verify debug mode is False
- [ ] Add input validation on all forms
- [ ] Add MIME type validation to file uploads
- [ ] Fix admin route protection on user listing routes
- [ ] Add authorization checks (user can only modify their own data)

### Before Scaling:
- [ ] Add Flask logging/audit trail
- [ ] Implement email verification flow
- [ ] Add account lockout mechanism
- [ ] Add error handlers for 404/500
- [ ] Enable HSTS and HTTPS redirect
- [ ] Add session timeout
- [ ] Remove/hide user emails from public views
- [ ] Add database backup automation

### Ongoing:
- [ ] Regular security audits
- [ ] Keep dependencies updated (pin versions)
- [ ] Monitor for suspicious activity
- [ ] Implement intrusion detection
- [ ] Test all authentication flows regularly

---

## Code Quality Issues

1. **Unused imports** - Check for removed dependencies
2. **Magic strings** - Use constants for status values ('pending', 'confirmed', 'cancelled')
3. **Error messages** - Generic "Error occurred" better than full exceptions
4. **Pagination missing** - Admin views load all users/orders in memory
5. **No pagination** - `/admin/users` could crash with thousands of users
6. **Code organization** - 2353 lines in one file; split into blueprints/modules

---

## Dependencies to Add

```
Flask-WTF>=1.2.0          # CSRF protection
Flask-Limiter>=3.3.0      # Rate limiting
python-magic>=0.4.27      # MIME type detection  
email-validator>=2.0.0    # Email validation
python-dateutil>=2.8.0    # Date parsing
PyYAML>=6.0               # Config management
```

---

## Environment Variables (Production)

Create `.env` file (add to `.gitignore`):
```
SECRET_KEY=<generate with secrets.token_hex(32)>
DATABASE_URL=postgresql://user:pass@host/db
FLASK_ENV=production
FLASK_DEBUG=False
MAX_UPLOAD_SIZE_MB=16
SESSION_TIMEOUT_MINUTES=30
```

---

## Testing Recommendations

- [ ] Add unit tests for all routes
- [ ] Add integration tests for authentication
- [ ] Test CSRF protection works
- [ ] Test rate limiting blocks abuse
- [ ] Security scanning: `bandit`, `safety`, `OWASP ZAP`
- [ ] Load testing for performance

