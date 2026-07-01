"""Pytest setup and shared fixtures."""
import os
import pytest
from app import create_app, db, bcrypt


@pytest.fixture
def app():
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["MAIL_USERNAME"] = ""
    os.environ["REDIS_URL"] = ""

    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["CACHE_TYPE"] = "SimpleCache"
    app.rq_queue = type('Queue', (), {'enqueue': lambda *a, **k: None})()

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_user(app, email, password, name, role="user", email_verified=1):
    with app.app_context():
        from app.models import User
        user = User(
            email=email,
            password=bcrypt.generate_password_hash(password).decode("utf-8"),
            name=name,
            role=role,
            email_verified=email_verified,
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def _create_car(app, seller_id, **kwargs):
    with app.app_context():
        from app.models import Car
        car = Car(
            seller_id=seller_id,
            make=kwargs.get("make", "Toyota"),
            model=kwargs.get("model", "Corolla"),
            year=kwargs.get("year", 2020),
            price=kwargs.get("price", 1500000.0),
            mileage=kwargs.get("mileage", 50000),
            transmission=kwargs.get("transmission", "Automatic"),
            condition=kwargs.get("condition", "Used"),
            description=kwargs.get("description", "Clean car"),
            status=kwargs.get("status", "active"),
        )
        db.session.add(car)
        db.session.commit()
        return car.id


@pytest.fixture
def auth_client(client, app):
    def _auth(email, password, name, role="user"):
        user_id = _create_user(app, email, password, name, role)
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user_id)
            sess["_fresh"] = True
        return client, user_id
    return _auth


@pytest.fixture
def admin_id(app):
    return _create_user(app, "admin@sarkinmota.com", "AdminPass1!", "Admin User", role="admin")


@pytest.fixture
def seller_id(app):
    return _create_user(app, "seller@sarkinmota.com", "SellerPass1!", "Seller User")


@pytest.fixture
def buyer_id(app):
    return _create_user(app, "buyer@sarkinmota.com", "BuyerPass1!", "Buyer User")


@pytest.fixture
def admin_client(client, admin_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_id)
        sess["_fresh"] = True
    return client


@pytest.fixture
def seller_client(client, seller_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(seller_id)
        sess["_fresh"] = True
    return client


@pytest.fixture
def buyer_client(client, buyer_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(buyer_id)
        sess["_fresh"] = True
    return client


@pytest.fixture
def active_car_id(app, seller_id):
    return _create_car(app, seller_id)


@pytest.fixture
def admin_user(app, admin_id):
    return admin_id


@pytest.fixture
def buyer_user(app, buyer_id):
    return buyer_id


@pytest.fixture
def seller_user(app, seller_id):
    return seller_id


@pytest.fixture
def active_listing(app, seller_id):
    from app.models import Car
    with app.app_context():
        car = Car(
            seller_id=seller_id,
            make="Toyota",
            model="Camry",
            year=2022,
            price=2500000.0,
            status="active",
        )
        db.session.add(car)
        db.session.commit()
        return car.id


def _get_by_id(app, model, id_):
    with app.app_context():
        return model.query.get(id_)
