"""Add performance indexes for frequent query paths.

Added indexes:
- cars(seller_id)
- orders(buyer_id), orders(car_id), orders(status), orders(created_at)
- notifications(user_id), notifications(is_read) + composite (user_id, is_read)
- saved_cars(user_id), saved_cars(car_id)
- users(role)

Revision ID: d2a3f5b7c9e1
Revises: 72a23b6ab245
Create Date: 2026-08-31
"""
from alembic import op


revision = "d2a3f5b7c9e1"
down_revision = "72a23b6ab245"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_cars_seller_id", "cars", ["seller_id"], unique=False)
    op.create_index("ix_orders_buyer_id", "orders", ["buyer_id"], unique=False)
    op.create_index("ix_orders_car_id", "orders", ["car_id"], unique=False)
    op.create_index("ix_orders_status", "orders", ["status"], unique=False)
    op.create_index("ix_orders_created_at", "orders", ["created_at"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False)
    op.create_index("ix_notifications_user_is_read", "notifications", ["user_id", "is_read"], unique=False)
    op.create_index("ix_saved_cars_user_id", "saved_cars", ["user_id"], unique=False)
    op.create_index("ix_saved_cars_car_id", "saved_cars", ["car_id"], unique=False)
    op.create_index("ix_users_role", "users", ["role"], unique=False)


def downgrade():
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_saved_cars_car_id", table_name="saved_cars")
    op.drop_index("ix_saved_cars_user_id", table_name="saved_cars")
    op.drop_index("ix_notifications_user_is_read", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_car_id", table_name="orders")
    op.drop_index("ix_orders_buyer_id", table_name="orders")
    op.drop_index("ix_cars_seller_id", table_name="cars")
