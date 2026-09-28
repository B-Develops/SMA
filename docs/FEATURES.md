# Sarkin Mota Autos - Features Overview

A comprehensive car marketplace web application built with Flask, PostgreSQL, and vanilla JavaScript.

## 🌟 Core Features

### For Buyers

- **Browse Listings** - View all available cars with advanced filtering
- **Search & Filter** - Filter by make, model, year, price, mileage, transmission
- **Place Bids** - Submit bids on cars you're interested in
- **Watchlist** - Save cars to track them
- **Notifications** - Get alerts for bids, messages, and price drops
- **Profile Management** - Manage your account and preferences

### For Sellers

- **Create Listings** - List cars with photos and details
- **Manage Listings** - Edit, update, or delete your listings
- **View Bids** - See all bids on your cars
- **Accept/Reject Bids** - Decide which bids to accept
- **Track Views** - Monitor listing performance

### For Administrators

- **Dashboard** - Overview of platform statistics
- **User Management** - View and manage all users
- **Listing Management** - Moderate and remove listings
- **Bid Management** - Cancel problematic bids
- **Platform Analytics** - Track growth and activity

---

## 📱 Pages & Routes

### Public Pages

| Route     | Description             |
| --------- | ----------------------- |
| `/`       | Landing page            |
| `/login`  | User login              |
| `/signup` | User registration       |
| `/browse` | Browse all car listings |
| `/about`  | About page              |

### User Dashboard

| Route            | Description             |
| ---------------- | ----------------------- |
| `/dashboard`     | Main user dashboard     |
| `/profile`       | User profile management |
| `/bids/my-bids`  | Bids you've placed      |
| `/bids/received` | Bids on your listings   |
| `/saved-cars`    | Watchlist               |
| `/notifications` | Notification center     |

### Listing Management

| Route               | Description          |
| ------------------- | -------------------- |
| `/cars/list`        | Create new listing   |
| `/cars/my-listings` | Manage your listings |
| `/cars/edit/<id>`   | Edit listing         |
| `/cars/<id>`        | View listing details |

### Admin Panel

| Route             | Description     |
| ----------------- | --------------- |
| `/admin`          | Admin dashboard |
| `/admin/users`    | Manage users    |
| `/admin/listings` | Manage listings |
| `/admin/bids`     | Manage bids     |

---

## 🔔 Notification Types

| Type               | Trigger                    | Recipient     |
| ------------------ | -------------------------- | ------------- |
| `bid_received`     | Someone bids on your car   | Seller        |
| `bid_accepted`     | Your bid is accepted       | Bidder        |
| `bid_rejected`     | Your bid is rejected       | Bidder        |
| `message_received` | New message received       | User          |
| `price_drop`       | Price dropped on saved car | Saved by user |
| `listing_expiring` | Listing expiring soon      | Seller        |
| `system`           | System announcements       | All users     |

---

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL 16+ (via SQLAlchemy; money stored as `NUMERIC(14,2)`)
- **Authentication**: Flask-Login
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Icons**: Lucide Icons
- **Fonts**: Google Fonts (Inter)
- **Styling**: Custom CSS with CSS Variables

---

## 📁 Project Structure

```
SarkinMota/
├── app.py                  # Main Flask application
├── init_db.py             # Database initialization
├── requirements.txt       # Python dependencies
├── .env                   # DATABASE_URL and secrets (gitignored)
├── static/               # Static assets
│   ├── *.css            # Stylesheets
│   └── Assets/          # Images and media
├── templates/           # Jinja2 templates
│   ├── dashboard.html  # Main dashboard layout
│   ├── login.html       # Login page
│   ├── Sign-up.html    # Registration page
│   ├── BrowseCars.html # Browse listings
│   └── dashboard/      # Dashboard pages
│       ├── Index.html
│       ├── Profile.html
│       ├── Messages.html
│       ├── Notifications.html
│       ├── ListCars.html
│       ├── BrowseCars.html
│       └── Admin*.html  # Admin pages
└── docs/               # Documentation
    ├── backend_phases.md
    ├── PHASE_7_NOTIFICATIONS.md
    └── PHASE_8_ADMIN.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
cd SarkinMota

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Run the application
python app.py
```

### Access

- Open http://localhost:5000 in your browser
- Login with test account: `basheer@example.com` / `password123`

---

## 🔒 Security Features

- Password hashing with Werkzeug
- Session-based authentication
- Admin access control
- SQL injection prevention
- Secure file uploads
- Input sanitization

---

## 📊 Bid Status Flow

```
active → accepted (seller accepts)
active → rejected (seller rejects)
active → cancelled (admin cancels)
accepted → cancelled (admin cancels)
```

---

## 📝 License

This project is for educational purposes.

---

## 📧 Support

For questions or issues, please open a GitHub issue.
