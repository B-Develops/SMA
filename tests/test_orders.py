"""Orders blueprint tests."""
import pytest
from app import db
from app.models import Order


class TestMyOrders:
    def test_my_orders_page_loads(self, client, buyer_id, app):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.get("/orders/my-orders")
        assert response.status_code == 200

    def test_my_orders_lists_only_own(self, client, app, buyer_id, seller_id, active_listing):
        with app.app_context():
            from app.models import Car
            order1 = Order(
                buyer_id=buyer_id,
                car_id=active_listing,
                order_amount=2500000.0,
                listed_price=2500000.0,
                status="pending",
            )
            other_car = Car(
                seller_id=seller_id,
                make="Honda",
                model="Accord",
                year=2019,
                price=1700000.0,
                status="active",
            )
            db.session.add(other_car)
            db.session.flush()
            order2 = Order(
                buyer_id=seller_id,
                car_id=other_car.id,
                order_amount=other_car.price,
                listed_price=other_car.price,
                status="pending",
            )
            db.session.add(order1)
            db.session.add(order2)
            db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.get("/orders/my-orders")
        assert response.status_code == 200

    def test_cancel_pending_order(self, client, app, buyer_id, active_listing):
        with app.app_context():
            order = Order(
                buyer_id=buyer_id,
                car_id=active_listing,
                order_amount=2500000.0,
                listed_price=2500000.0,
                status="pending",
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.post(f"/orders/{order_id}/cancel")

        assert response.status_code == 302
        with app.app_context():
            order = Order.query.get(order_id)
            assert order.status == "cancelled"

    def test_cancel_completed_order_blocked(self, client, app, buyer_id, active_listing):
        with app.app_context():
            order = Order(
                buyer_id=buyer_id,
                car_id=active_listing,
                order_amount=2500000.0,
                listed_price=2500000.0,
                status="completed",
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id

        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.post(f"/orders/{order_id}/cancel")

        assert response.status_code == 302
        with app.app_context():
            order = Order.query.get(order_id)
            assert order.status == "completed"
