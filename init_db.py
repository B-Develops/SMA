# init_db.py
from app import app, db, bcrypt
from app.models import User, Order, Car, Payment, SavedCar, Notification, NotificationSettings, AdminActionLog

with app.app_context():
    db.create_all()
    print("Database tables created!")
    
    # Check if test user already exists
    existing_user = User.query.filter_by(email='test@example.com').first()
    if not existing_user:
        hashed_password = bcrypt.generate_password_hash('password123').decode('utf-8')
        user = User(email='test@example.com', password=hashed_password)
        db.session.add(user)
        db.session.commit()
        print("Test user created: test@example.com / password123")
    else:
        print("Test user already exists")
