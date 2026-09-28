"""Initial migration: create the base schema.

SarkinMota is PostgreSQL-only. This revision is the re-baselined head of the
chain so that a brand new PostgreSQL database can be brought up with nothing
but ``flask db upgrade`` -- previously this revision only dropped an index on
``orders`` and assumed the table already existed, which made replaying the
chain from zero impossible on any new server.

The base tables are created here in the shape they had at the start of the
chain. Later revisions add payments, email-verification columns, password
reset tokens, indexes, and the PostgreSQL-native type changes.

Every statement here is unconditional because Alembic's ``alembic_version``
table already guarantees this revision runs exactly once. Probing for existing
tables would break ``flask db upgrade --sql``, where ``op.get_bind()`` returns a
mock connection that cannot answer catalog queries.
"""
from alembic import op
import sqlalchemy as sa

revision = "6cf388f0ae84"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password", sa.String(length=256), nullable=False),
        sa.Column("name", sa.String(length=100)),
        sa.Column("phone", sa.String(length=20)),
        sa.Column("location", sa.String(length=100)),
        sa.Column("bio", sa.Text()),
        sa.Column("role", sa.String(length=20)),
        sa.Column("email_verified", sa.Integer()),
        sa.Column("phone_verified", sa.Integer()),
        sa.Column("id_verified", sa.Integer()),
        sa.Column("address_verified", sa.Integer()),
        sa.Column("failed_login_attempts", sa.Integer()),
        sa.Column("last_failed_login", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "cars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("make", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("year", sa.Integer()),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("mileage", sa.Integer()),
        sa.Column("transmission", sa.String(length=20)),
        sa.Column("condition", sa.String(length=20)),
        sa.Column("description", sa.Text()),
        sa.Column("image_url", sa.String(length=256)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("created_at", sa.DateTime()),
        sa.ForeignKeyConstraint(
            ["seller_id"], ["users.id"], name="fk_cars_seller_id_users"
        ),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("car_id", sa.Integer(), nullable=False),
        sa.Column("order_amount", sa.Float(), nullable=False),
        sa.Column("listed_price", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20)),
        sa.Column("payment_method", sa.String(length=50)),
        sa.Column("delivery_address", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("confirmed_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("cancelled_at", sa.DateTime()),
        sa.ForeignKeyConstraint(
            ["buyer_id"], ["users.id"], name="fk_orders_buyer_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["car_id"], ["cars.id"], name="fk_orders_car_id_cars"
        ),
    )

    # The original intent of this revision: the (buyer_id, car_id) index was
    # too restrictive, because a buyer may re-order a car after cancelling.
    # IF EXISTS because a database created straight from the models never had it.
    op.execute("DROP INDEX IF EXISTS uq_orders_buyer_car")

    op.create_table(
        "saved_cars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("car_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_saved_cars_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["car_id"], ["cars.id"], name="fk_saved_cars_car_id_cars"
        ),
        sa.UniqueConstraint("user_id", "car_id", name="unique_user_car"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("link", sa.String(length=256)),
        sa.Column("is_read", sa.Integer()),
        sa.Column("created_at", sa.DateTime()),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notifications_user_id_users"
        ),
    )

    op.create_table(
        "notification_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email_order_notifications", sa.Integer()),
        sa.Column("email_message_notifications", sa.Integer()),
        sa.Column("email_order_accepted", sa.Integer()),
        sa.Column("email_price_drop", sa.Integer()),
        sa.Column("push_new_orders", sa.Integer()),
        sa.Column("push_messages", sa.Integer()),
        sa.Column("push_order_accepted", sa.Integer()),
        sa.Column("in_app_notifications", sa.Integer()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notification_settings_user_id_users",
        ),
        sa.UniqueConstraint("user_id", name="uq_notification_settings_user_id"),
    )

    # admin_action_logs had no migration of its own (it was only ever created by
    # db.create_all()), so a database built from the migration chain alone was
    # missing the table and crashed on the first admin audit write.
    op.create_table(
        "admin_action_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.Integer()),
        sa.Column("details", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
        sa.ForeignKeyConstraint(
            ["admin_id"], ["users.id"], name="fk_admin_action_logs_admin_id_users"
        ),
    )


def downgrade():
    op.drop_table("admin_action_logs")
    op.drop_table("notification_settings")
    op.drop_table("notifications")
    op.drop_table("saved_cars")
    op.drop_table("orders")
    op.drop_table("cars")
    op.drop_table("users")
