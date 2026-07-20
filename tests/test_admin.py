"""Admin blueprint tests."""
import pytest
from app import db
from app.models import User, Car, Order, AdminActionLog


class TestAdminAccess:
    def test_admin_dashboard_loads(self, client, admin_id, app):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_id)
            sess["_fresh"] = True

        response = client.get("/admin/")
        assert response.status_code == 200

    def test_non_admin_blocked(self, client, buyer_id, app):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.get("/admin/")
        assert response.status_code == 403

    def test_non_admin_blocked_from_users_page(self, client, buyer_id):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.get("/admin/users")
        assert response.status_code == 403

    def test_non_admin_blocked_from_listings_page(self, client, buyer_id):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.get("/admin/listings")
        assert response.status_code == 403

    def test_non_admin_blocked_from_orders_page(self, client, buyer_id):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.get("/admin/orders")
        assert response.status_code == 403

    def test_non_admin_blocked_from_audit_logs(self, client, buyer_id):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.get("/admin/audit-logs")
        assert response.status_code == 403

    def test_non_admin_blocked_from_delete_user(self, client, buyer_id, admin_id):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.post(f"/admin/users/{admin_id}/delete")
        assert response.status_code == 403

    def test_non_admin_blocked_from_delete_listing(self, client, buyer_id, active_listing):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(buyer_id)
            sess["_fresh"] = True

        response = client.post(f"/admin/listings/{active_listing}/delete")
        assert response.status_code == 403

    def test_non_admin_blocked_from_accept_order(self, client, buyer_id, app, active_listing):
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

        response = client.post(f"/admin/orders/{order_id}/accept")
        assert response.status_code == 403

    def test_non_admin_blocked_from_reject_order(self, client, buyer_id, app, active_listing):
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

        response = client.post(f"/admin/orders/{order_id}/reject")
        assert response.status_code == 403

    def test_non_admin_blocked_from_cancel_order(self, client, buyer_id, app, active_listing):
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

        response = client.post(f"/admin/orders/{order_id}/cancel")
        assert response.status_code == 403


class TestAdminUsers:
    def test_users_page_loads(self, admin_client):
        response = admin_client.get("/admin/users")
        assert response.status_code == 200

    def test_users_pagination_page_2(self, admin_client):
        response = admin_client.get("/admin/users/page/2")
        assert response.status_code == 200

    def test_admin_cannot_delete_self(self, admin_client, admin_id):
        response = admin_client.post(f"/admin/users/{admin_id}/delete")
        assert response.status_code == 302


class TestAdminListings:
    def test_listings_page_loads(self, admin_client, active_listing):
        response = admin_client.get("/admin/listings")
        assert response.status_code == 200

    def test_listings_pagination(self, admin_client):
        response = admin_client.get("/admin/listings/page/2")
        assert response.status_code == 200


class TestAdminOrders:
    def test_orders_page_loads(self, admin_client, active_listing, buyer_id, app):
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

        response = admin_client.get("/admin/orders")
        assert response.status_code == 200

    def test_accept_order(self, admin_client, app, active_listing, buyer_id):
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

        response = admin_client.post(f"/admin/orders/{order_id}/accept")

        assert response.status_code == 302
        with app.app_context():
            order = Order.query.get(order_id)
            assert order.status == "confirmed"

    def test_reject_order(self, admin_client, app, active_listing, buyer_id):
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

        response = admin_client.post(f"/admin/orders/{order_id}/reject")

        assert response.status_code == 302
        with app.app_context():
            order = Order.query.get(order_id)
            assert order.status == "cancelled"
