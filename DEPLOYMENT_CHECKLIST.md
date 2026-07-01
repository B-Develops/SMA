# Production Deployment Checklist

## Pre-Deployment Security Review

### Authentication & Access Control
- [ ] Verify `SECRET_KEY` is NOT the debug default
- [ ] Verify `FLASK_DEBUG = False` in production
- [ ] Add password complexity requirements (12+ chars, mixed case, numbers)
- [ ] Implement email verification before account activation
- [ ] Add account lockout after 5 failed login attempts
- [ ] Implement session timeout (30 minutes recommended)
- [ ] Add "remember me" functionality with secure tokens
- [ ] Implement logout on all sessions when password changes

### CSRF & Request Protection
- [ ] Add Flask-WTF CSRF tokens to all forms
- [ ] Enable CSRF protection on all state-changing endpoints
- [ ] Test CSRF protection with curl/Postman

### Rate Limiting
- [ ] Rate limit login endpoint (5 attempts/minute)
- [ ] Rate limit signup endpoint (3 attempts/hour)
- [ ] Rate limit order placement (prevent spam)
- [ ] Rate limit file uploads
- [ ] Test rate limiting blocks abuse

### Input Validation
- [ ] Email validation on signup
- [ ] Name validation (no special chars that could cause XSS)
- [ ] Price validation (positive, reasonable max)
- [ ] Year validation (1900-current year+1)
- [ ] Description length limits
- [ ] File upload extension whitelist
- [ ] File upload MIME type validation
- [ ] File size limits enforced

### File Upload Security
- [ ] MIME type validation (magic bytes, not extension only)
- [ ] Virus scanning on uploads (optional but recommended)
- [ ] Store uploads outside web root
- [ ] Serve uploads through controlled endpoint
- [ ] Rename uploads to prevent enumeration
- [ ] Set proper file permissions (644)

### API Security
- [ ] No sensitive data in JSON responses (emails, phone numbers)
- [ ] Proper authorization checks (user can only access own data)
- [ ] No SQL injection in raw queries (use ORM or parameterized)
- [ ] No exposed stack traces in production
- [ ] Proper 403 responses for unauthorized access
- [ ] Proper 404 responses for not found resources

### Data Protection
- [ ] All passwords hashed with bcrypt (not plain text)
- [ ] No sensitive fields logged (passwords, tokens)
- [ ] Database backups encrypted
- [ ] Database backups tested for recovery
- [ ] Sensitive fields masked in admin views
- [ ] PII (Personally Identifiable Information) handled per regulations

### HTTP Security
- [ ] HTTPS enforced (redirect HTTP to HTTPS)
- [ ] HSTS header enabled
- [ ] Secure cookies (HttpOnly, Secure, SameSite)
- [ ] CORS configured if needed
- [ ] X-Frame-Options set to prevent clickjacking
- [ ] X-Content-Type-Options set to nosniff
- [ ] CSP header configured
- [ ] Referrer-Policy set

### Error Handling
- [ ] Custom error pages for 404, 500, 403
- [ ] No stack traces shown to users in production
- [ ] Errors logged to file, not console
- [ ] Proper HTTP status codes used
- [ ] Generic error messages to users
- [ ] Detailed error logs for administrators

### Logging & Monitoring
- [ ] Audit logging for sensitive actions:
  - [ ] User registration
  - [ ] User login/logout
  - [ ] Password changes
  - [ ] Admin actions (delete, modify)
  - [ ] Failed authentication attempts
  - [ ] File uploads
  - [ ] Order changes
- [ ] Logs stored securely (not in git)
- [ ] Log rotation configured
- [ ] Log retention policy (90 days minimum)
- [ ] Alert system for suspicious activity

### Dependencies
- [ ] All dependencies in requirements.txt with pinned versions
- [ ] No test/dev dependencies in production requirements
- [ ] Dependencies checked for known vulnerabilities
- [ ] `pip install -r requirements.txt` works without errors
- [ ] `pip install pipdeptree` and review dependency tree

### Database
- [ ] Database normalized (no duplicate data)
- [ ] Foreign key constraints enforced
- [ ] NOT NULL constraints on required fields
- [ ] Unique constraints on email, usernames
- [ ] Indexes on frequently queried columns
- [ ] Database user has limited permissions (not admin)
- [ ] Database connections use SSL/TLS
- [ ] Database password NOT hardcoded
- [ ] Database backups automated
- [ ] Backup recovery tested

### Environment Configuration
- [ ] .env file created (NOT in version control)
- [ ] .env.example provided with dummy values
- [ ] All secrets in .env (not in code)
- [ ] DATABASE_URL configured
- [ ] SECRET_KEY generated securely
- [ ] FLASK_ENV=production
- [ ] MAX_CONTENT_LENGTH set appropriately
- [ ] Timezone configuration

### Testing
- [ ] Unit tests written for critical functions
- [ ] Integration tests for authentication flows
- [ ] CSRF protection tested
- [ ] Rate limiting tested
- [ ] Input validation tested with malicious inputs
- [ ] Authorization tested (try accessing others' data)
- [ ] Error handling tested
- [ ] Load testing (capacity planning)
- [ ] Security scanning with:
  - [ ] `bandit` for Python code vulnerabilities
  - [ ] `safety` for dependency vulnerabilities
  - [ ] OWASP ZAP for web vulnerabilities

### Code Quality
- [ ] No hardcoded credentials
- [ ] No debug print statements left
- [ ] No `TODO` comments without tickets
- [ ] Code reviewed by another developer
- [ ] Linting passes (pylint, flake8)
- [ ] Unused imports removed
- [ ] Dead code removed
- [ ] Magic numbers replaced with constants
- [ ] Comments for complex logic

### Monitoring & Alerting
- [ ] Error monitoring (Sentry, DataDog, etc.)
- [ ] Performance monitoring
- [ ] Uptime monitoring
- [ ] Alert on repeated 500 errors
- [ ] Alert on unusual error patterns
- [ ] Alert on database connection failures

### Deployment Process
- [ ] Deployment documentation written
- [ ] Database migration plan
- [ ] Rollback plan documented
- [ ] Zero-downtime deployment strategy
- [ ] Staging environment mirrors production
- [ ] Test full deployment process in staging

### Infrastructure
- [ ] Web server (Gunicorn/uWSGI) configured
- [ ] Reverse proxy (Nginx) configured
- [ ] SSL/TLS certificates valid
- [ ] Firewall rules configured
- [ ] Only necessary ports open
- [ ] DDoS protection configured
- [ ] WAF (Web Application Firewall) configured
- [ ] CDN configured for static assets

### Documentation
- [ ] Deployment guide written
- [ ] Architecture documented
- [ ] Security policies documented
- [ ] Incident response plan documented
- [ ] Admin procedures documented
- [ ] Database schema documented

### Post-Deployment
- [ ] Test all critical user flows
- [ ] Test all admin functions
- [ ] Verify HTTPS working
- [ ] Verify security headers present
- [ ] Verify rate limiting working
- [ ] Check error logs
- [ ] Monitor system resources (CPU, memory, disk)
- [ ] Verify backups working

---

## Quick Hardening Checklist (Priority Order)

### Fix Today (Critical):
1. [ ] Set proper `SECRET_KEY` from environment
2. [ ] Set `FLASK_DEBUG = False`
3. [ ] Add Flask-WTF CSRF protection
4. [ ] Add email validation to signup
5. [ ] Add rate limiting to login
6. [ ] Fix admin route protection (remove from user routes)
7. [ ] Add security headers (X-Frame-Options, CSP, etc.)
8. [ ] Ensure all passwords are bcrypt hashed

### Fix This Week (High):
9. [ ] Add Flask-Limiter
10. [ ] Add MIME type validation to file uploads
11. [ ] Add authorization checks
12. [ ] Add error handlers
13. [ ] Add audit logging
14. [ ] Remove hardcoded test data

### Fix This Month (Medium):
15. [ ] Add email verification
16. [ ] Implement account lockout
17. [ ] Add session timeout
18. [ ] Add comprehensive input validation
19. [ ] Set up automated backups
20. [ ] Add security scanning (bandit, safety)

---

## Commands to Run Before Deploying

```bash
# Install dependencies with pinned versions
pip install -r requirements.txt

# Check for known vulnerabilities
pip install safety
safety check

# Check Python code for security issues
pip install bandit
bandit -r .

# Check for SQL injection and other issues
pip install semgrep
semgrep --config=p/security-audit .

# Run tests
pytest

# Verify no debug statements
grep -r "print(" --include="*.py" app.py | grep -v "^#"
grep -r "DEBUG" --include="*.py" app.py | grep -v "^#"

# Check for hardcoded credentials
grep -r "password=" --include="*.py" .
grep -r "SECRET" --include="*.py" . | grep -v ".env"

# Verify security headers
curl -i http://localhost:5000 | grep -i "X-Content-Type\|X-Frame\|Content-Security"
```

---

## Monitoring in Production

1. **Error Tracking**: Use Sentry, DataDog, or similar
2. **Performance**: Monitor response times, database queries
3. **Security**: Monitor failed login attempts, 403 errors
4. **Infrastructure**: Monitor CPU, memory, disk, network
5. **Backups**: Verify daily backup completion

---

## Incident Response

Create a runbook for:
- Database corruption/loss
- Security breach detected
- DDoS attack
- Service outage
- Data exposure (unauthorized access)

