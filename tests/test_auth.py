"""Auth blueprint tests."""
import pytest
from app.models import User, Order, SavedCar, AdminActionLog
from app import db, bcrypt


def _get_user_by_email(app, email):
    with app.app_context():
        return User.query.filter_by(email=email).first()


def _create_user(app, email, password, name):
    with app.app_context():
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(
            email=email,
            password=hashed,
            name=name,
            role="user",
            email_verified=1,
        )
        db.session.add(user)
        db.session.commit()
        return user.id


class TestSignup:
    def test_signup_page_loads(self, client):
        response = client.get("/auth/signup")
        assert response.status_code == 200

    def test_signup_success(self, client, app):
        with app.app_context():
            db.session.remove()
            initial_count = User.query.count()

        response = client.post(
            "/auth/signup",
            data={
                "name": "Test User",
                "email": "test@validmail.com",
                "password": "SecurePass1!",
            },
            follow_redirects=False,
        )

        with app.app_context():
            assert User.query.count() == initial_count + 1

    def test_signup_duplicate_email(self, client, app):
        email = "dupe@example.com"
        _create_user(app, email, "ExistingPass1!", "Existing")

        with app.app_context():
            initial_count = User.query.count()

        response = client.post(
            "/auth/signup",
            data={
                "name": "Another",
                "email": email,
                "password": "SecurePass1!",
            },
        )

        assert response.status_code == 302
        with app.app_context():
            assert User.query.count() == initial_count

    def test_signup_short_password(self, client):
        response = client.post(
            "/auth/signup",
            data={
                "name": "Short",
                "email": "short@example.com",
                "password": "123",
            },
        )

        assert response.status_code == 302


class TestLogin:
    def test_login_page_loads(self, client):
        response = client.get("/auth/login")
        assert response.status_code == 200

    def test_login_success(self, client, app):
        email = "login_success@example.com"
        _create_user(app, email, "CorrectPass1!", "Login User")

        response = client.post(
            "/auth/login",
            data={
                "email": email,
                "password": "CorrectPass1!",
            },
        )

        assert response.status_code == 302


class TestDeleteAccount:
    def test_user_can_delete_own_account(self, client, app, buyer_id):
        with app.app_context():
            user = User.query.get(buyer_id)
            original_email = user.email

        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.post("/settings/delete-account")

        assert response.status_code == 302
        with app.app_context():
            user = User.query.get(buyer_id)
            assert user is not None
            assert user.email == f"deleted_{buyer_id}@anonymized.local"
            assert user.name == "Deleted User"
            assert user.password == "DELETED"
            assert user.email_verified == 0
            orders = Order.query.filter_by(buyer_id=buyer_id).count()
            assert orders == 0
            saved = SavedCar.query.filter_by(user_id=buyer_id).count()
            assert saved == 0
            log = AdminActionLog.query.filter_by(
                action="user_deleted_self",
                resource_id=buyer_id
            ).first()
            assert log is not None

    def test_deleted_user_cannot_access_protected_routes(self, client, app, buyer_id):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        client.post("/settings/delete-account")

        response = client.get("/dashboard")
        assert response.status_code == 302
