"""Move the schema to PostgreSQL-native types.

SarkinMota is now PostgreSQL-only. This revision finishes that move:

- Money columns (cars.price, orders.order_amount, orders.listed_price,
  payments.amount) become NUMERIC(14, 2). double precision cannot represent
  kobo exactly, so sums of order amounts drifted by fractions of a naira.
- Status and flag columns get NOT NULL plus a server_default. cars/routes.py
  inserts listings with a raw text() INSERT that omits `status`; with only a
  Python-side default those rows landed with status = NULL and vanished from
  every status-filtered query.
- CHECK constraints for roles, years, and non-negative money.
- Indexes for the browse filters that Postgres now has to serve:
  cars(status), cars(make), cars(price), orders(buyer_id, status),
  password_reset_tokens(user_id), admin_action_logs(admin_id, created_at).

Revision ID: c4e91b0a7d52
Revises: d2a3f5b7c9e1
Create Date: 2026-09-27
"""
from alembic import op
import sqlalchemy as sa

revision = "c4e91b0a7d52"
down_revision = "d2a3f5b7c9e1"
branch_labels = None
depends_on = None

MONEY = sa.Numeric(14, 2, asdecimal=True)

# Column -> (existing nullable, new server_default)
BACKFILL_SERVER_DEFAULTS = {
    "users": {
        "email_verified": "0",
        "phone_verified": "0",
        "id_verified": "0",
        "address_verified": "0",
        "failed_login_attempts": "0",
        "role": "'user'",
    },
    "cars": {"status": "'active'"},
    "orders": {"status": "'pending'"},
    "payments": {
        "currency": "'NGN'",
        "provider": "'unset'",
        "status": "'pending'",
    },
    "notifications": {"is_read": "0"},
    "notification_settings": {
        "email_order_notifications": "1",
        "email_message_notifications": "1",
        "email_order_accepted": "1",
        "email_price_drop": "1",
        "push_new_orders": "1",
        "push_messages": "1",
        "push_order_accepted": "1",
        "in_app_notifications": "1",
    },
    "password_reset_tokens": {"used": "0"},
}


def upgrade():
    # ------------------------------------------------------------------
    # 1. Money: double precision -> NUMERIC(14, 2)
    # ------------------------------------------------------------------
    for table, column in (
        ("cars", "price"),
        ("orders", "order_amount"),
        ("orders", "listed_price"),
        ("payments", "amount"),
    ):
        op.alter_column(
            table,
            column,
            type_=MONEY,
            existing_type=sa.Float(),
            postgresql_using=f"{column}::numeric(14, 2)",
        )

    # ------------------------------------------------------------------
    # 2. NOT NULL + server defaults for status/flag columns.
    #    Backfill first so a legacy NULL cannot block the constraint.
    # ------------------------------------------------------------------
    for table, columns in BACKFILL_SERVER_DEFAULTS.items():
        for column, default in columns.items():
            op.execute(
                sa.text(
                    f'UPDATE "{table}" SET "{column}" = {default} '
                    f'WHERE "{column}" IS NULL'
                )
            )
            op.alter_column(
                table,
                column,
                nullable=False,
                server_default=sa.text(default),
            )

    # ------------------------------------------------------------------
    # 3. CHECK constraints
    # ------------------------------------------------------------------
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'admin')")
    op.create_check_constraint(
        "ck_users_failed_login_attempts", "users", "failed_login_attempts >= 0"
    )
    op.create_check_constraint(
        "ck_cars_year", "cars", "year IS NULL OR year BETWEEN 1900 AND 2100"
    )
    op.create_check_constraint("ck_cars_price_non_negative", "cars", "price >= 0")
    op.create_check_constraint(
        "ck_orders_amount_non_negative", "orders", "order_amount >= 0"
    )
    op.create_check_constraint(
        "ck_orders_listed_price_non_negative", "orders", "listed_price >= 0"
    )
    op.create_check_constraint(
        "ck_payments_amount_non_negative", "payments", "amount >= 0"
    )

    # ------------------------------------------------------------------
    # 4. Indexes for the browse and dashboard query paths
    # ------------------------------------------------------------------
    op.create_index("ix_cars_status", "cars", ["status"], unique=False)
    op.create_index("ix_cars_make", "cars", ["make"], unique=False)
    op.create_index("ix_cars_price", "cars", ["price"], unique=False)
    op.create_index(
        "ix_orders_buyer_status", "orders", ["buyer_id", "status"], unique=False
    )
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_action_logs_admin_created",
        "admin_action_logs",
        ["admin_id", "created_at"],
        unique=False,
    )
    # notification_settings.user_id uniqueness is created by the initial
    # migration (uq_notification_settings_user_id), so it is not repeated here.


def downgrade():
    op.drop_index("ix_admin_action_logs_admin_created", table_name="admin_action_logs")
    op.drop_index(
        "ix_password_reset_tokens_user_id", table_name="password_reset_tokens"
    )
    op.drop_index("ix_orders_buyer_status", table_name="orders")
    op.drop_index("ix_cars_price", table_name="cars")
    op.drop_index("ix_cars_make", table_name="cars")
    op.drop_index("ix_cars_status", table_name="cars")

    op.drop_constraint("ck_payments_amount_non_negative", "payments", type_="check")
    op.drop_constraint(
        "ck_orders_listed_price_non_negative", "orders", type_="check"
    )
    op.drop_constraint("ck_orders_amount_non_negative", "orders", type_="check")
    op.drop_constraint("ck_cars_price_non_negative", "cars", type_="check")
    op.drop_constraint("ck_cars_year", "cars", type_="check")
    op.drop_constraint("ck_users_failed_login_attempts", "users", type_="check")
    op.drop_constraint("ck_users_role", "users", type_="check")

    for table, columns in BACKFILL_SERVER_DEFAULTS.items():
        for column in columns:
            op.alter_column(
                table,
                column,
                nullable=True,
                server_default=None,
            )

    for table, column in (
        ("cars", "price"),
        ("orders", "order_amount"),
        ("orders", "listed_price"),
        ("payments", "amount"),
    ):
        op.alter_column(
            table,
            column,
            type_=sa.Float(),
            existing_type=MONEY,
            postgresql_using=f"{column}::double precision",
        )
