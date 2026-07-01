"""
Script to export Admin Dashboard values to a text file
This can be converted to .doc format
"""
import sqlite3
from datetime import datetime

# Connect to database
conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get current timestamp
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

output = []
output.append("=" * 70)
output.append("SARKIN MOTA AUTOS - ADMIN DASHBOARD REPORT")
output.append(f"Generated on: {timestamp}")
output.append("=" * 70)
output.append("")

# ===== STATS =====
output.append("-" * 50)
output.append("STATISTICS OVERVIEW")
output.append("-" * 50)

# Total Users
cursor.execute("SELECT COUNT(*) FROM users")
total_users = cursor.fetchone()[0]
output.append(f"Total Users:           {total_users}")

# Admin Users
cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
admin_count = cursor.fetchone()[0]
output.append(f"Admin Users:            {admin_count}")

# Total Listings
cursor.execute("SELECT COUNT(*) FROM cars")
total_listings = cursor.fetchone()[0]
output.append(f"Total Listings:         {total_listings}")

# Active Listings
cursor.execute("SELECT COUNT(*) FROM cars WHERE status = 'active'")
active_listings = cursor.fetchone()[0]
output.append(f"Active Listings:        {active_listings}")

# Sold Listings
cursor.execute("SELECT COUNT(*) FROM cars WHERE status = 'sold'")
sold_listings = cursor.fetchone()[0]
output.append(f"Cars Sold:              {sold_listings}")

# Total Bids
cursor.execute("SELECT COUNT(*) FROM bids")
total_bids = cursor.fetchone()[0]
output.append(f"Total Bids:             {total_bids}")

# Active Bids
cursor.execute("SELECT COUNT(*) FROM bids WHERE status = 'active'")
active_bids = cursor.fetchone()[0]
output.append(f"Active Bids:            {active_bids}")

# Average Price
cursor.execute("SELECT AVG(price) FROM cars")
avg_price = cursor.fetchone()[0]
if avg_price is None:
    avg_price = 0
output.append(f"Average Price:          ₦{avg_price:,.2f}")

output.append("")

# ===== ADMIN ACCOUNTS =====
output.append("-" * 50)
output.append("ADMIN ACCOUNTS")
output.append("-" * 50)

cursor.execute("""
    SELECT id, name, email, role, created_at
    FROM users
    WHERE role = 'admin'
    ORDER BY created_at DESC
""")
admins = cursor.fetchall()

if admins:
    for i, admin in enumerate(admins, 1):
        output.append(f"\nAdmin #{i}:")
        output.append(f"  Name:         {admin['name'] if admin['name'] else 'N/A'}")
        output.append(f"  Email:        {admin['email']}")
        output.append(f"  Role:         {admin['role']}")
        output.append(f"  Created:      {admin['created_at']}")
else:
    output.append("No admin accounts found.")

output.append("")

# ===== RECENT LISTINGS =====
output.append("-" * 50)
output.append("RECENT LISTINGS (Last 5)")
output.append("-" * 50)

cursor.execute("""
    SELECT cars.*, users.name AS seller_name
    FROM cars
    JOIN users ON cars.seller_id = users.id
    ORDER BY cars.created_at DESC
    LIMIT 5
""")
listings = cursor.fetchall()

if listings:
    for i, car in enumerate(listings, 1):
        output.append(f"\nListing #{i}:")
        output.append(f"  Car:          {car['year']} {car['make']} {car['model']}")
        output.append(f"  Seller:       {car['seller_name']}")
        output.append(f"  Price:        ₦{car['price']:,.2f}")
        output.append(f"  Status:       {car['status']}")
        output.append(f"  Listed:       {car['created_at']}")
else:
    output.append("No listings found.")

output.append("")

# ===== ALL LISTINGS SUMMARY =====
output.append("-" * 50)
output.append("ALL LISTINGS SUMMARY")
output.append("-" * 50)

cursor.execute("""
    SELECT cars.*, users.name AS seller_name
    FROM cars
    JOIN users ON cars.seller_id = users.id
    ORDER BY cars.created_at DESC
""")
all_listings = cursor.fetchall()

if all_listings:
    output.append(f"\nTotal: {len(all_listings)} listings\n")
    for i, car in enumerate(all_listings, 1):
        output.append(f"{i}. {car['year']} {car['make']} {car['model']} - ₦{car['price']:,.0f} ({car['status']})")
else:
    output.append("No listings found.")

output.append("")

# ===== ALL USERS SUMMARY =====
output.append("-" * 50)
output.append("ALL USERS SUMMARY")
output.append("-" * 50)

cursor.execute("SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC")
users = cursor.fetchall()

if users:
    output.append(f"\nTotal: {len(users)} users\n")
    for i, user in enumerate(users, 1):
        output.append(f"{i}. {user['name'] if user['name'] else user['email']} ({user['role']}) - {user['created_at']}")
else:
    output.append("No users found.")

output.append("")

# ===== ALL BIDS SUMMARY =====
output.append("-" * 50)
output.append("ALL BIDS SUMMARY")
output.append("-" * 50)

cursor.execute("""
    SELECT bids.*, cars.make, cars.model
    FROM bids
    JOIN cars ON bids.car_id = cars.id
    ORDER BY bids.created_at DESC
""")
bids = cursor.fetchall()

if bids:
    output.append(f"\nTotal: {len(bids)} bids\n")
    for i, bid in enumerate(bids, 1):
        output.append(f"{i}. Bid ₦{bid['bid_amount']:,.0f} on {bid['make']} {bid['model']} (Status: {bid['status']}) - {bid['created_at']}")
else:
    output.append("No bids found.")

output.append("")
output.append("=" * 70)
output.append("END OF REPORT")
output.append("=" * 70)

# Write to file
with open('AdminDashboard_Report.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print("Admin Dashboard Report generated successfully!")
print("Output file: AdminDashboard_Report.txt")

conn.close()
