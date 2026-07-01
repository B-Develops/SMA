# Ordering System Documentation

## Overview

The Sarkin Mota Autos platform has been converted from a **bidding system** to a **direct ordering system**. Users can now place orders (offers) on cars directly instead of bidding in an auction format.

---

## Database Schema

### Orders Table

The `orders` table replaces the old `bids` table.

```sql
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    car_id INTEGER NOT NULL,
    order_amount REAL NOT NULL,        -- The offer amount placed by buyer
    listed_price REAL NOT NULL,        -- Original car price at time of order
    status TEXT DEFAULT 'pending',     -- pending, confirmed, processing, shipped, delivered, cancelled, refunded, completed
    payment_method TEXT,               -- bank_transfer, cash, card, etc.
    delivery_address TEXT,             -- Optional delivery address
    notes TEXT,                        -- Additional notes from buyer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES users (id),
    FOREIGN KEY (car_id) REFERENCES cars (id)
);
```

#### Status Flow

- **pending** – Order placed, awaiting seller confirmation
- **confirmed** – Seller accepted the order
- **processing** – Payment processed, preparing delivery (optional future state)
- **shipped** – Car in transit (optional future state)
- **delivered** – Order completed, car delivered (optional future state)
- **cancelled** – Order cancelled by buyer or seller
- **refunded** – Payment refunded (optional future state)
- **completed** – Order fully fulfilled (alternative to delivered)

Currently used statuses: `pending`, `confirmed`, `cancelled`.

---

## API Routes

### User Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/cars/<car_id>/order` | POST | Place a new order on a car |
| `/orders` | GET | View all orders (My Orders page) |
| `/orders/<order_id>/cancel` | POST | Cancel a pending/confirmed order |

### Admin Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/admin/orders` | GET | List all orders (admin) |
| `/admin/orders/<order_id>/accept` | POST | Accept a pending order |
| `/admin/orders/<order_id>/reject` | POST | Reject a pending order (cancels) |
| `/admin/orders/<order_id>/cancel` | POST | Cancel any non-completed order |

### Backward Compatibility Redirects

Old bid routes are redirected to new order routes to prevent broken links:

| Old Route | New Route |
|-----------|-----------|
| `/admin/bids` | `/admin/orders` |
| `/admin/bids/<id>/cancel` | `/admin/orders` |
| `/bids/<id>/cancel` | `/dashboard` |
| `/cars/<id>/bid` | Redirect with info message |

---

## Templates

### User-Facing

| Template | Purpose |
|----------|---------|
| `dashboard/Listing-Page.html` | Car detail page with order form |
| `dashboard.html` | User dashboard with active orders section |
| `MyOrders.html` | Full order history page |
| `BrowseCars.html` | Car listing grid with order button |

### Admin-Facing

| Template | Purpose |
|----------|---------|
| `AdminOrders.html` | Admin orders management table |
| `AdminDashboard.html` | Admin home with orders stats |
| `AdminUsers.html` | Admin users list (orders count column available) |
| `AdminListings.html` | Admin listings management |

---

## Migration Strategy

### Automatic Database Migration

When `init_db()` runs, the `migrate_bids_to_orders()` function automatically:

1. Creates the new `orders` table if not exists
2. Copies all existing `bids` to `orders` with status mapping:
   - `active` → `pending`
   - `accepted` → `confirmed`
   - `rejected` → `cancelled`
   - `cancelled` → `cancelled`
3. Migrates `notification_settings` column names:
   - `email_bid_notifications` → `email_order_notifications`
   - `email_bid_accepted` → `email_order_accepted`
   - `push_new_bids` → `push_new_orders`
   - `push_bid_accepted` → `push_order_accepted`
4. Drops the old `bids` table

**Note:** This migration runs only once. Existing data is preserved with status conversions.

---

## Notification Settings

### Email Preferences

| Setting | Description |
|---------|-------------|
| `email_order_notifications` | Notify when someone places an order on your listing |
| `email_order_accepted` | Notify when your order is confirmed by seller |
| `email_message_notifications` | Notify for new messages |
| `email_price_drop` | Notify when a saved car's price drops |

### Push Preferences

| Setting | Description |
|---------|-------------|
| `push_new_orders` | Browser push for new orders on your listings |
| `push_order_accepted` | Browser push when your order is accepted |
| `push_messages` | Browser push for new messages |

---

## User Statistics

The `User.get_stats()` method now returns:

```python
{
    'total_listings': int,
    'active_listings': int,
    'sold_listings': int,
    'total_orders': int,
    'pending_orders': int,
    'confirmed_orders': int,
    'saved_cars': int
}
```

---

## Changes Summary

### Backend (app.py)

- Renamed `bids` table to `orders`
- Renamed columns: `bidder_id` → `buyer_id`, `bid_amount` → `order_amount`
- Added additional order tracking fields: `listed_price`, `payment_method`, `delivery_address`, `notes`, timestamps
- Updated all route handlers to use `/order` endpoints
- Updated admin dashboard statistics to count orders
- Updated notification settings to use order terminology
- Added backward compatibility redirects

### Frontend (Templates)

- Replaced all "bid" and "bidding" copy with "order" and "ordering"
- Updated form actions: `/cars/<id>/bid` → `/cars/<id>/order`
- Updated form fields: `bid_amount` → `order_amount`
- Updated status badges to use order statuses
- Updated navigation tabs (Admin Bids → Admin Orders)
- Updated dashboard statistics and order listings
- Updated help/FAQ content

---

## Testing Checklist

- [ ] Place a new order on a car
- [ ] View order in "My Orders" page
- [ ] Cancel an order from dashboard
- [ ] Admin accepts order → status becomes confirmed
- [ ] Admin rejects order → status becomes cancelled
- [ ] Admin cancels any order
- [ ] Delete a car listing → associated orders removed
- [ ] Delete user account → user's orders deleted
- [ ] Notification settings save correctly with new field names
- [ ] Old `/admin/bids` URL redirects to `/admin/orders`
- [ ] BrowseCars page order form submits correctly
- [ ] Dashboard statistics reflect correct counts

---

## Rollback Plan

If needed to revert to bidding system:

1. Restore database from backup before migration
2. Restore `app.py` from version control prior to changes
3. Restore all templates from version control

**Note:** No automated rollback exists; manual restoration required.

---

## Future Enhancements (Optional)

- Add order status history tracking (audit log)
- Implement payment integration (status → `processing`, `completed`)
- Add delivery tracking (status → `shipped`, `delivered`)
- Seller-side order management interface
- Order receipts/invoices
- Email notifications for order events
- Push notifications for order updates

---

*Last updated: 2026-04-29*
