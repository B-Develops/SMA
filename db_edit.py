import sqlite3

conn = sqlite3.connect("database.db")  # same name as in get_db_connection()
cursor = conn.cursor()

# add role column
try:
    cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    print("role column added")
except:
    print("role column already exists")

# make admin
cursor.execute(
    "UPDATE users SET role = 'admin' WHERE email = ?",
    ("admin@sarkinmota.com",)
)

conn.commit()
conn.close()

print("done")