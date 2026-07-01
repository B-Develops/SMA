# Sarkin Mota Autos - Backend Phases

This document provides an overview of all backend implementation phases for the Sarkin Mota Autos car marketplace application.

## Overview

The backend is implemented as a Flask application (`app.py`) with SQLite database, Flask-Login authentication, and comprehensive RESTful API routes.

---

## Phase 1: Core Authentication

**Status**: ✅ Complete

### Features

- User registration with email/password
- User login/logout with session management
- Password hashing with Werkzeug security
- Remember me functionality

### Database Tables

- `users` - User accounts with email, password_hash, name, phone, bio

### Routes

- `GET /signup` - Registration page
- `POST /signup` - Create new account
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /logout` - End session

### Documentation

- See [`app.py`](app.py) lines 1-150 for implementation

---

## Phase 2: User Profile Management

**Status**: ✅ Complete

### Features

- Profile viewing and editing
- Profile image upload
- Bio and contact information management

### Database Extensions

- `users.image_url` - Profile picture path

### Routes

- `GET /profile` - View profile
- `POST /profile` - Update profile

### Documentation

- See [`app.py`](app.py) lines 151-280 for implementation

---

## Phase 3: Car Listings

**Status**: ✅ Complete

### Features

- Create car listings with full details
- Edit and delete own listings
- Image upload for car photos
- Listing status management (active/sold)

### Database Tables

- `cars` - Car listings with make, model, year, price, mileage, description, images

### Routes

- `GET /cars/list` - Create listing page
- `POST /cars/list` - Save new listing
- `GET /cars/edit/<id>` - Edit listing
- `POST /cars/edit/<id>` - Update listing
- `POST /cars/delete/<id>` - Delete listing
- `GET /cars/my-listings` - View own listings

### Documentation

- See [`app.py`](app.py) lines 281-450 for implementation

---

## Phase 4: Bidding System

**Status**: ✅ Complete

### Features

- Place bids on car listings
- View bid history
- Accept/reject bids (for sellers)
- Bid status tracking (active/accepted/rejected/cancelled)

### Database Tables

- `bids` - Bid records with amount, status, timestamps

### Routes

- `POST /cars/<car_id>/bid` - Place a bid
- `POST /bids/<bid_id>/accept` - Accept bid (seller only)
- `POST /bids/<bid_id>/reject` - Reject bid (seller only)
- `GET /bids/my-bids` - View my bids
- `GET /bids/received` - View bids on my listings

### Documentation

- See [`app.py`](app.py) lines 451-620 for implementation

---

## Phase 5: Browse & Search

**Status**: ✅ Complete

### Features

- Browse all car listings
- Advanced search filters (make, model, year range, price range, mileage, transmission)
- Save cars to watchlist
- View saved cars

### Database Tables

- `saved_cars` - User's watchlist

### Routes

- `GET /browse` - Browse listings with filters
- `GET /api/cars/search` - Search API endpoint
- `POST /cars/<car_id>/save` - Save to watchlist
- `POST /cars/<car_id>/unsave` - Remove from watchlist
- `GET /saved-cars` - View watchlist

### Documentation

- See [`app.py`](app.py) lines 621-775 for implementation

---

## Phase 6: Image Upload

**Status**: ✅ Complete

### Features

- Upload car images to server
- Support for multiple image formats (PNG, JPG, JPEG, GIF)
- Secure filename handling
- Image serving via static files

### Routes

- `POST /upload` - Handle image uploads

### Documentation

- See [`app.py`](app.py) lines 776-880 for implementation

---

## Phase 7: Notifications & Alerts

**Status**: ✅ Complete

### Features

- Notification center for users
- Multiple notification types:
  - `bid_received` - Someone bid on your car
  - `bid_accepted` - Your bid was accepted
  - `bid_rejected` - Your bid was rejected
  - `message_received` - New message received
  - `price_drop` - Price dropped on saved car
  - `listing_expiring` - Listing expiring soon
  - `system` - System announcements
- Mark notifications as read
- Delete notifications
- Unread count badge

### Database Tables

- `notifications` - User notifications

### Helper Functions

- [`create_notification()`](app.py) - Create new notification
- [`get_user_notifications()`](app.py) - Fetch user notifications
- [`get_unread_count()`](app.py) - Get unread notification count
- [`mark_notification_read()`](app.py) - Mark single notification read
- [`mark_all_notifications_read()`](app.py) - Mark all as read
- [`delete_notification()`](app.py) - Delete notification

### Routes

- `GET /notifications` - Notification center
- `POST /notifications/mark-read/<id>` - Mark as read
- `POST /notifications/mark-all-read` - Mark all as read
- `POST /notifications/delete/<id>` - Delete notification
- `GET /api/notifications/count` - Get unread count API

### Templates

- [`templates/dashboard/Notifications.html`](templates/dashboard/Notifications.html)

### Documentation

- See [`docs/PHASE_7_NOTIFICATIONS.md`](docs/PHASE_7_NOTIFICATIONS.md)

---

## Phase 8: Admin Features

**Status**: ✅ Complete

### Features

- Admin dashboard with platform statistics
- User management (view, anonymize users)
- Listing management (view, delete listings)
- Bid management (view, cancel bids)
- Admin-only routes with access control

### Database Extensions

- `users.is_admin` - Admin flag (boolean)

### Decorators

- `@admin_required` - Admin access control decorator

### Routes

- `GET /admin` - Admin dashboard
- `GET /admin/users` - Manage users
- `POST /admin/users/<id>/delete` - Anonymize user
- `GET /admin/listings` - Manage listings
- `POST /admin/listings/<id>/delete` - Delete listing
- `GET /admin/bids` - Manage bids
- `POST /admin/bids/<id>/cancel` - Cancel bid

### Templates

- [`templates/dashboard/AdminDashboard.html`](templates/dashboard/AdminDashboard.html)
- [`templates/dashboard/AdminUsers.html`](templates/dashboard/AdminUsers.html)
- [`templates/dashboard/AdminListings.html`](templates/dashboard/AdminListings.html)
- [`templates/dashboard/AdminBids.html`](templates/dashboard/AdminBids.html)

### Documentation

- See [`docs/PHASE_8_ADMIN.md`](docs/PHASE_8_ADMIN.md)

---

## Database Schema

```
users
  id (INTEGER PRIMARY KEY)
  email (TEXT UNIQUE)
  password_hash (TEXT)
  name (TEXT)
  phone (TEXT)
  bio (TEXT)
  image_url (TEXT)
  is_admin (INTEGER DEFAULT 0)
  created_at (DATETIME)

cars
  id (INTEGER PRIMARY KEY)
  seller_id (INTEGER FK)
  make (TEXT)
  model (TEXT)
  year (INTEGER)
  price (REAL)
  mileage (INTEGER)
  transmission (TEXT)
  description (TEXT)
  image_url (TEXT)
  status (TEXT default 'active')
  views (INTEGER default 0)
  created_at (DATETIME)

bids
  id (INTEGER PRIMARY KEY)
  car_id (INTEGER FK)
  bidder_id (INTEGER FK)
  amount (REAL)
  status (TEXT default 'active')
  created_at (DATETIME)

saved_cars
  id (INTEGER PRIMARY KEY)
  user_id (INTEGER FK)
  car_id (INTEGER FK)
  created_at (DATETIME)

notifications
  id (INTEGER PRIMARY KEY)
  user_id (INTEGER FK)
  type (TEXT)
  title (TEXT)
  message (TEXT)
  related_id (INTEGER)
  is_read (INTEGER default 0)
  created_at (DATETIME)
```

---

## Getting Started

### Installation

```bash
pip install -r requirements.txt
```

### Initialize Database

```bash
python init_db.py
```

### Run Application

```bash
python app.py
```

### Test Accounts

- **Admin**: basheer@example.com / password123
- **Regular User**: test@example.com / password123

---

## API Endpoints Summary

| Method | Endpoint                        | Description                   |
| ------ | ------------------------------- | ----------------------------- |
| GET    | `/api/notifications/count`      | Get unread notification count |
| POST   | `/cars/<id>/bid`                | Place a bid                   |
| GET    | `/api/cars/search`              | Search cars with filters      |
| POST   | `/cars/<id>/save`               | Save car to watchlist         |
| POST   | `/notifications/mark-read/<id>` | Mark notification read        |
| POST   | `/admin/users/<id>/delete`      | Delete user (admin)           |
| POST   | `/admin/listings/<id>/delete`   | Delete listing (admin)        |
| POST   | `/admin/bids/<id>/cancel`       | Cancel bid (admin)            |

---

## Security Features

- Password hashing with Werkzeug
- Session-based authentication
- Admin route protection
- Input sanitization
- CSRF protection via Flask-WTF (implicit)
- SQL injection prevention via parameterized queries

---

## Future Enhancements

- Real-time notifications (WebSockets)
- Email notifications
- Payment processing integration
- Multi-image gallery for listings
- Advanced analytics dashboard
- User verification system
