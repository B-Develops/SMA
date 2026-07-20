"""Cars blueprint tests."""
import pytest
from app import db
from app.models import User, Car, Order, SavedCar


class TestCarListing:
    def test_list_car_page_loads(self, client, seller_id, app):
        with app.app_context():
            from app.models import User
            user = User.query.get(seller_id)
            assert user is not None

    def test_place_order_creates_order(self, client, app, buyer_id, active_listing):
        with app.app_context():
            from app.models import User
            buyer = User.query.get(buyer_id)
            buyer.phone = "+234801234567"
            buyer.location = "Lagos"
            db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.post(
            f"/cars/cars/{active_listing}/order",
            data={
                "order_amount": 2500000.0,
                "payment_method": "cash",
                "delivery_address": "Lagos",
            },
        )

        assert response.status_code == 302
        with app.app_context():
            order = Order.query.filter_by(
                buyer_id=buyer_id, car_id=active_listing
            ).first()
            assert order is not None
            assert order.status == "pending"
            assert order.order_amount == 2500000.0

    def test_save_car_creates_saved_car(self, client, app, buyer_id, active_listing):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.post(f"/cars/cars/{active_listing}/save")

        assert response.status_code == 302
        with app.app_context():
            saved = SavedCar.query.filter_by(
                user_id=buyer_id, car_id=active_listing
            ).first()
            assert saved is not None

    def test_unsave_car_deletes_saved_car(self, client, app, buyer_id, active_listing):
        with app.app_context():
            saved = SavedCar(user_id=buyer_id, car_id=active_listing)
            db.session.add(saved)
            db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.post(f"/cars/cars/{active_listing}/unsave")

        assert response.status_code == 302
        with app.app_context():
            saved = SavedCar.query.filter_by(
                user_id=buyer_id, car_id=active_listing
            ).first()
            assert saved is None
