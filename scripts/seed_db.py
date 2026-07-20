# seed_db.py - Production database seed script
# Usage: python scripts/seed_db.py
from app import create_app, db
from app.models import User, Car

def seed():
    app = create_app()
    with app.app_context():
        # Create a demo seller if none exists
        demo_seller = User.query.filter_by(email='seller@sarkinmota.com').first()
        if not demo_seller:
            from app import bcrypt
            hashed = bcrypt.generate_password_hash('SecurePass123!').decode('utf-8')
            demo_seller = User(
                email='seller@sarkinmota.com',
                password=hashed,
                name='Demo Seller',
                phone='+234801234567',
                location='Lagos, Nigeria',
                role='user'
            )
            db.session.add(demo_seller)
            db.session.commit()
            print("Created demo seller: seller@sarkinmota.com / SecurePass123!")
        else:
            print("Demo seller already exists")
        
        # Create a demo buyer if none exists
        demo_buyer = User.query.filter_by(email='buyer@sarkinmota.com').first()
        if not demo_buyer:
            from app import bcrypt
            hashed = bcrypt.generate_password_hash('SecurePass123!').decode('utf-8')
            demo_buyer = User(
                email='buyer@sarkinmota.com',
                password=hashed,
                name='Demo Buyer',
                phone='+234809876543',
                location='Abuja, Nigeria',
                role='user'
            )
            db.session.add(demo_buyer)
            db.session.commit()
            print("Created demo buyer: buyer@sarkinmota.com / SecurePass123!")
        else:
            print("Demo buyer already exists")
        
        print("Database seeded successfully!")

if __name__ == '__main__':
    seed()
