from app import db
from app.models import Notification, User
from app.utils import create_order_notification


def test_create_order_notification_persists_in_app_update(app):
    with app.app_context():
        user = User(
            email="notify@example.com",
            password="hashed",
            name="Notifier",
            role="user",
            email_verified=1,
        )
        db.session.add(user)
        db.session.commit()

        notification = create_order_notification(
            user_id=user.id,
            order_id=77,
            event_type="order_received",
            title="Order received",
            message="Your order has been received and is being reviewed.",
        )

        saved = Notification.query.get(notification.id)

        assert saved is not None
        assert saved.user_id == user.id
        assert saved.type == "order_received"
        assert saved.title == "Order received"
        assert saved.link == "/orders/77"
        assert saved.is_read == 0
