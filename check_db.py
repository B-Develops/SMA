import sqlite3
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables found:')
for table in tables:
    table_name = table[0]
    print('  {}'.format(table_name))
    if table_name == 'users':
        cursor.execute('SELECT id, email, name FROM {}'.format(table_name))
        users = cursor.fetchall()
        print('    Users: {}'.format(len(users)))
        for user in users[:3]:  # Show first 3 users
            print('      ID: {}, Email: {}, Name: {}'.format(user[0], user[1], user[2]))
    elif table_name == 'cars':
        cursor.execute('SELECT id, make, model, year FROM {}'.format(table_name))
        cars = cursor.fetchall()
        print('    Cars: {}'.format(len(cars)))
        for car in cars[:3]:  # Show first 3 cars
            print('      ID: {}, Make: {}, Model: {}, Year: {}'.format(car[0], car[1], car[2], car[3]))

conn.close()