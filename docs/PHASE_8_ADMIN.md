# Phase 8: Admin Features

## Overview

The Admin Features system provides administrative control over the Sarkin Mota Autos platform, allowing admins to manage users, listings, bids, and view platform analytics.

## Admin Access

### How to Become an Admin

Admin status is set via the `is_admin` column in the `users` table:

- `is_admin = 1` → Admin user
- `is_admin = 0` → Regular user

### Admin Check

```python
# Check if current user is admin
if current_user.is_admin:
    # Allow access
else:
    # Redirect with error
```

## Database Schema

### No New Tables Required

Admin features use existing tables:

- `users` - User management
- `cars` - Listing management
- `bids` - Bid management
- `saved_cars` - Saved cars data

## Admin Routes

### Admin Dashboard

- **Route:** `/admin`
- **Method:** GET
- **Access:** Admin only
- **Description:** Main admin dashboard with overview stats

### User Management

| Route                      | Method | Description            |
| -------------------------- | ------ | ---------------------- |
| `/admin/users`             | GET    | List all users         |
| `/admin/users/<id>`        | GET    | View user details      |
| `/admin/users/<id>/delete` | POST   | Delete/deactivate user |

### Listing Management

| Route                          | Method | Description          |
| ------------------------------ | ------ | -------------------- |
| `/admin/listings`              | GET    | List all listings    |
| `/admin/listings/<id>`         | GET    | View listing details |
| `/admin/listings/<id>/approve` | POST   | Approve listing      |
| `/admin/listings/<id>/reject`  | POST   | Reject listing       |
| `/admin/listings/<id>/delete`  | POST   | Delete listing       |

### Bid Management

| Route                     | Method | Description   |
| ------------------------- | ------ | ------------- |
| `/admin/bids`             | GET    | List all bids |
| `/admin/bids/<id>/cancel` | POST   | Cancel a bid  |

### Analytics

- **Route:** `/admin/analytics`
- **Method:** GET
- **Access:** Admin only
- **Description:** View platform statistics and metrics

## Analytics Metrics

### User Metrics

- Total users
- Active users (logged in within 30 days)
- New users (last 30 days)
- Admin users count

### Listing Metrics

- Total listings
- Active listings
- Sold listings
- Average price
- Listings by make

### Bid Metrics

- Total bids
- Active bids
- Average bid amount
- Bids per listing ratio

## Backend Functions

### Admin Check

```python
def is_admin(user_id):
    """Check if user is admin."""
    conn = get_db_connection()
    user = conn.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return user and user["is_admin"] == 1
```

### Admin Routes Middleware

All admin routes should include:

```python
@app.route("/admin/...")
@login_required
def admin_page():
    if not current_user.is_admin:
        flash("Admin access required.", "error")
        return redirect(url_for("dashboard"))
    # ... route logic
```

## Template Files

- `templates/dashboard/AdminDashboard.html` - Main admin dashboard
- `templates/dashboard/AdminUsers.html` - User management
- `templates/dashboard/AdminListings.html` - Listing management
- `templates/dashboard/AdminBids.html` - Bid management
- `templates/dashboard/AdminAnalytics.html` - Analytics page

## Security Considerations

### Access Control

1. All admin routes require `@login_required`
2. Additional `is_admin` check on every admin route
3. Users cannot access admin URLs directly

### Audit Logging (Future)

- Log admin actions (who did what and when)
- Track listing approvals/rejections
- Monitor user deletions

## Usage Examples

### Adding Admin User via SQL

```sql
-- Make user ID 1 an admin
UPDATE users SET is_admin = 1 WHERE id = 1;

-- Check if user is admin
SELECT is_admin FROM users WHERE id = 1;
```

### Testing Admin Access

1. Log in as admin user (basheer@example.com)
2. Navigate to `/admin`
3. View dashboard statistics
4. Test user/listing management features

## Future Enhancements

- Bulk actions (approve multiple listings)
- User banning instead of deletion
- Detailed audit logs
- Admin notification settings
- Role-based permissions (super admin, moderator)
