# init_db.py
import os
from app import create_app, db, bcrypt
from app.models import User, Order, Car, Payment, SavedCar, Notification, NotificationSettings, AdminActionLog

app = create_app()

with app.app_context():
    db.create_all()
    print("Database tables created!")

    if os.environ.get("CREATE_TEST_USER", "False") == "True":
        existing_user = User.query.filter_by(email='test@example.com').first()
        if not existing_user:
            hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
            user = User(email='test@example.com', password=hashed_password)
            db.session.add(user)
            db.session.commit()
            print("Test user created: test@example.com / password123")
        else:
            print("Test user already exists")
    else:
        print("Skipping test user creation (set CREATE_TEST_USER=True to enable)")