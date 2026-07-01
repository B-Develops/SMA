# Phase 7: Notifications & Alerts

## Overview

The Notifications & Alerts system keeps users informed about important events related to their account, listings, and activity on Sarkin Mota Autos.

## Features

### Notification Types

| Type               | Description                          | Icon |
| ------------------ | ------------------------------------ | ---- |
| `bid_received`     | Someone placed a bid on your listing | 💰   |
| `bid_accepted`     | Your bid was accepted by the seller  | ✅   |
| `bid_rejected`     | Your bid was rejected by the seller  | ❌   |
| `message_received` | You received a new message           | 💬   |
| `price_drop`       | Price dropped on a saved car         | 📉   |
| `listing_sold`     | Your listing was marked as sold      | 💰   |
| `listing_expiring` | Your listing is expiring soon        | ⚠️   |

### Database Schema

#### Notifications Table

```sql
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT,
    link TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
```

### API Routes

#### View Notifications

- **Route:** `/notifications`
- **Method:** GET
- **Access:** Authenticated users
- **Description:** Displays all notifications for the current user

#### Mark Single Notification as Read

- **Route:** `/notifications/mark-read/<id>`
- **Method:** POST
- **Access:** Authenticated users (owner only)

#### Mark All Notifications as Read

- **Route:** `/notifications/mark-all-read`
- **Method:** POST
- **Access:** Authenticated users

#### Delete Notification

- **Route:** `/notifications/delete/<id>`
- **Method:** POST
- **Access:** Authenticated users (owner only)

#### Get Unread Count (API)

- **Route:** `/api/notifications/count`
- **Method:** GET
- **Access:** Authenticated users
- **Returns:** JSON `{"unread_count": N}`

### Backend Functions

#### Database Functions

| Function                                                   | Description                           |
| ---------------------------------------------------------- | ------------------------------------- |
| `init_notifications_db()`                                  | Creates the notifications table       |
| `create_notification(user_id, type, title, message, link)` | Creates a new notification            |
| `get_user_notifications(user_id, unread_only, limit)`      | Retrieves user notifications          |
| `get_unread_count(user_id)`                                | Returns count of unread notifications |
| `mark_notification_read(notification_id, user_id)`         | Marks notification as read            |
| `mark_all_notifications_read(user_id)`                     | Marks all notifications as read       |
| `delete_notification(notification_id, user_id)`            | Deletes a notification                |

## Usage Examples

### Creating a Notification

```python
# When someone places a bid
create_notification(
    user_id=listing_owner_id,
    type="bid_received",
    title="New Bid on Your Toyota Camry",
    message="Basheer placed a bid of ₦16,000,000 on your listing",
    link="/cars/1"
)
```

### Getting User Notifications

```python
# Get all notifications
notifications = get_user_notifications(user_id=1)

# Get only unread
unread = get_user_notifications(user_id=1, unread_only=True)

# Get unread count for badge
count = get_unread_count(user_id=1)
```

## Template Files

- `templates/dashboard/Notifications.html` - Notification center UI

## Future Enhancements

- Email notifications for important alerts
- Push notifications (browser/mobile)
- Notification preferences per notification type
- Email digest (daily/weekly summary)
- Admin-initiated announcements
