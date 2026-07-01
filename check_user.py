from app import app, db, User, bcrypt
app.app_context().push()
user = User.query.filter_by(email='basheer@example.com').first()
if user:
    print(f"User found: {user.email}")
    print(f"Password hash: {user.password}")
    # Try checking if 'password' matches
    if bcrypt.check_password_hash(user.password, 'password'):
        print("Password 'password' matches!")
    else:
        print("Password 'password' does NOT match")
else:
    print("User not found")
