from flask import render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from ...models import User, Car, Order, NotificationSettings, AdminActionLog, Payment
from ... import db, cache
from datetime import datetime, timedelta
import json
from functools import wraps
from . import admin_bp


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def _get_admin_stats():
    total_users = User.query.count()
    admin_count = User.query.filter_by(role='admin').count()
    total_listings = Car.query.count()
    active_listings = Car.query.filter_by(status='active').count()
    sold_listings = Car.query.filter_by(status='sold').count()
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    confirmed_orders = Order.query.filter_by(status='confirmed').count()
    avg_price = db.session.query(db.func.avg(Car.price)).scalar() or 0
    return {
        "total_users": total_users,
        "admin_count": admin_count,
        "total_listings": total_listings,
        "active_listings": active_listings,
        "sold_listings": sold_listings,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "confirmed_orders": confirmed_orders,
        "avg_price": avg_price,
    }


def _get_platform_activity(days=7):
    """Return daily dashboard activity for the most recent calendar days."""
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days - 1)
    start_time = datetime.combine(start_date, datetime.min.time())

    activity = {
        "labels": [],
        "users": [],
        "listings": [],
        "completed_orders": [],
    }

    user_counts = {}
    for user in User.query.filter(User.created_at >= start_time).all():
        user_counts[user.created_at.date()] = user_counts.get(user.created_at.date(), 0) + 1

    listing_counts = {}
    for car in Car.query.filter(Car.created_at >= start_time).all():
        listing_counts[car.created_at.date()] = listing_counts.get(car.created_at.date(), 0) + 1

    completed_order_counts = {}
    completed_orders = Order.query.filter(
        Order.status == 'completed',
        Order.completed_at >= start_time,
    ).all()
    for order in completed_orders:
        completed_date = order.completed_at.date()
        completed_order_counts[completed_date] = completed_order_counts.get(completed_date, 0) + 1

    for offset in range(days):
        day = start_date + timedelta(days=offset)
        activity["labels"].append(day.strftime("%a"))
        activity["users"].append(user_counts.get(day, 0))
        activity["listings"].append(listing_counts.get(day, 0))
        activity["completed_orders"].append(completed_order_counts.get(day, 0))

    return activity


@admin_bp.route('/')
@admin_bp.route('/admin')
@login_required
@admin_required
def dashboard():
    stats = _get_admin_stats()
    platform_activity = _get_platform_activity()
    recent_listings = Car.query.join(User).order_by(Car.created_at.desc()).limit(5).all()
    active_admins = User.query.filter_by(role='admin').order_by(User.created_at.desc()).all()
    admin_accounts = []
    for admin in active_admins:
        admin_dict = {
            'id': admin.id,
            'name': admin.name or 'N/A',
            'email': admin.email,
            'phone': admin.phone or 'N/A',
            'created_at': admin.created_at,
            'updated_at': admin.updated_at,
            'email_verified': admin.email_verified
        }
        admin_accounts.append(admin_dict)

    return render_template(
        "AdminDashboard.html",
        stats=stats,
        platform_activity=platform_activity,
        recent_listings=recent_listings,
        admin_accounts=admin_accounts,
    )


@admin_bp.route('/users')
@admin_bp.route('/users/page/<int:page>')
@login_required
@admin_required
def users(page=1):
    cache_key = f"admin_users_page_{page}_{current_user.id}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    per_page = 25

    # Get paginated users with listing count
    users_query = db.session.query(
        User.id, User.email, User.name, User.phone, User.role, User.created_at,
        db.func.count(Car.id).label('listing_count')
    ).outerjoin(Car, User.id == Car.seller_id).group_by(User.id).order_by(User.created_at.desc())

    users_paginated = users_query.paginate(page=page, per_page=per_page, error_out=False)
    users_list = []

    for user in users_paginated.items:
        user_dict = {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'phone': user.phone,
            'role': user.role,
            'listing_count': user.listing_count or 0,
            'created_at': user.created_at
        }
        users_list.append(user_dict)

    response = render_template("AdminUsers.html",
                         users=users_list,
                         pagination=users_paginated)
    cache.set(cache_key, response, timeout=300)
    return response


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.dashboard'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))

    try:
        user.name = 'Deleted User'
        user.email = f"deleted_{user_id}@anonymized.local"
        user.password = 'DELETED'
        user.phone = None
        user.location = None
        user.bio = None
        user.email_verified = 0
        user.phone_verified = 0
        user.id_verified = 0
        user.address_verified = 0
        user.updated_at = datetime.utcnow()

        Order.query.filter_by(buyer_id=user_id).delete()
        SavedCar.query.filter_by(user_id=user_id).delete()
        NotificationSettings.query.filter_by(user_id=user_id).delete()

        admin_log = AdminActionLog(
            admin_id=current_user.id,
            action="anonymize_user",
            resource_type="User",
            resource_id=user_id,
            details=f"Anonymized account {user.email}"
        )
        db.session.add(admin_log)

        db.session.commit()
        cache.clear()
        flash('User account has been anonymized.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.route('/listings')
@admin_bp.route('/listings/page/<int:page>')
@login_required
@admin_required
def listings(page=1):
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    cache_key = f"admin_listings_page_{page}_{sort_by}_{sort_order}_{current_user.id}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    per_page = 25

    listings_query = Car.query.join(User)

    sort_map = {
        'make': Car.make,
        'model': Car.model,
        'year': Car.year,
        'price': Car.price,
        'status': Car.status,
        'created_at': Car.created_at,
        'mileage': Car.mileage
    }

    sort_column = sort_map.get(sort_by, Car.created_at)
    if sort_order == 'desc':
        listings_query = listings_query.order_by(sort_column.desc())
    else:
        listings_query = listings_query.order_by(sort_column.asc())

    listings_paginated = listings_query.paginate(page=page, per_page=per_page, error_out=False)
    listings_list = []

    for car in listings_paginated.items:
        car_dict = {
            'id': car.id,
            'make': car.make,
            'model': car.model,
            'year': car.year,
            'price': car.price,
            'mileage': car.mileage,
            'transmission': car.transmission,
            'condition': car.condition,
            'description': car.description,
            'image_url': car.image_url,
            'status': car.status,
            'created_at': car.created_at,
            'seller_name': car.seller.name if car.seller else '',
            'seller_email': car.seller.email if car.seller else ''
        }
        listings_list.append(car_dict)

    # include admin summary stats so templates can show totals
    stats = _get_admin_stats()

    response = render_template("AdminListings.html",
                         listings=listings_list,
                         pagination=listings_paginated,
                         current_sort=sort_by,
                         current_order=sort_order,
                         total_listings=stats.get('total_listings', 0),
                         active_listings=stats.get('active_listings', 0),
                         sold_listings=stats.get('sold_listings', 0))
    cache.set(cache_key, response, timeout=300)
    return response


@admin_bp.route('/listings/<int:listing_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_listing(listing_id):
    car = Car.query.get(listing_id)
    if not car:
        flash('Listing not found.', 'error')
        return redirect(url_for('admin.listings'))

    try:
        Order.query.filter_by(car_id=listing_id).delete()
        SavedCar.query.filter_by(car_id=listing_id).delete()
        db.session.delete(car)

        admin_log = AdminActionLog(
            admin_id=current_user.id,
            action="delete_listing",
            resource_type="Car",
            resource_id=listing_id,
            details=f"Deleted listing {listing_id} and its associated orders/saved-cars"
        )
        db.session.add(admin_log)

        db.session.commit()
        cache.clear()
        flash('Listing has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting listing: {str(e)}', 'error')

    return redirect(url_for('admin.listings'))


@admin_bp.route('/orders')
@admin_bp.route('/orders/page/<int:page>')
@login_required
@admin_required
def orders(page=1):
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    cache_key = f"admin_orders_page_{page}_{sort_by}_{sort_order}_{current_user.id}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    per_page = 25

    orders_query = db.session.query(
        Order,
        User.name.label('buyer_name'),
        User.email.label('buyer_email'),
        Car.make.label('make'),
        Car.model.label('model'),
        Car.year.label('year'),
        Car.price.label('car_price')
    ).outerjoin(User, Order.buyer_id == User.id)\
     .outerjoin(Car, Order.car_id == Car.id)

    sort_map = {
        'amount': Order.order_amount,
        'status': Order.status,
        'created_at': Order.created_at,
        'make': Car.make,
        'model': Car.model,
        'year': Car.year,
        'listed_price': Car.price
    }

    sort_column = sort_map.get(sort_by, Order.created_at)
    if sort_order == 'desc':
        orders_query = orders_query.order_by(sort_column.desc())
    else:
        orders_query = orders_query.order_by(sort_column.asc())

    orders_paginated = orders_query.paginate(page=page, per_page=per_page, error_out=False)
    orders_list = []

    order_ids = [order.Order.id for order in orders_paginated.items]
    payments_q = Payment.query.filter(Payment.order_id.in_(order_ids)).order_by(Payment.created_at.desc()).all()
    latest_payments = {}
    for payment in payments_q:
        if payment.order_id not in latest_payments:
            latest_payments[payment.order_id] = payment

    for order in orders_paginated.items:
        payment = latest_payments.get(order.Order.id)
        order_dict = {
            'id': order.Order.id,
            'buyer_name': order.buyer_name or 'Deleted User',
            'buyer_email': order.buyer_email or '',
            'year': order.year,
            'make': order.make,
            'model': order.model,
            'order_amount': order.Order.order_amount,
            'listed_price': order.car_price if order.car_price else 0,
            'status': order.Order.status,
            'created_at': order.Order.created_at,
            'payment_status': payment.status if payment else None,
            'payment_id': payment.id if payment else None,
            'payment_reference': payment.provider_reference if payment else None,
        }
        orders_list.append(order_dict)

    total_orders = orders_paginated.total
    active_orders = Order.query.filter_by(status='pending').count()

    response = render_template("AdminOrders.html",
                         orders=orders_list,
                         pagination=orders_paginated,
                         total_orders=total_orders,
                         active_orders=active_orders,
                         current_sort=sort_by,
                         current_order=sort_order)
    cache.set(cache_key, response, timeout=300)
    return response


@admin_bp.route('/orders/<int:order_id>/accept', methods=['POST'])
@login_required
@admin_required
def accept_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('admin.orders'))

    if order.status != 'pending':
        flash(f'Cannot accept order with status \'{order.status}\'.', 'error')
        return redirect(url_for('admin.orders'))

    try:
        order.status = 'confirmed'
        order.confirmed_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        db.session.commit()

        car = Car.query.get(order.car_id)
        car_label = f"{car.year} {car.make} {car.model}" if car else "your order"

        admin_log = AdminActionLog(
            admin_id=current_user.id,
            action="accept_order",
            resource_type="Order",
            resource_id=order.id,
            details=f"Confirmed order #{order.id} (buyer_id={order.buyer_id})"
        )
        db.session.add(admin_log)

        db.session.commit()
        flash('Order has been confirmed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error accepting order: {str(e)}', 'error')

    cache.clear()
    return redirect(url_for('admin.orders'))


@admin_bp.route('/orders/<int:order_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('admin.orders'))

    if order.status != 'pending':
        flash(f'Cannot reject order with status \'{order.status}\'.', 'error')
        return redirect(url_for('admin.orders'))

    try:
        order.status = 'cancelled'
        order.cancelled_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        db.session.commit()

        car = Car.query.get(order.car_id)
        car_label = f"{car.year} {car.make} {car.model}" if car else "your order"

        admin_log = AdminActionLog(
            admin_id=current_user.id,
            action="reject_order",
            resource_type="Order",
            resource_id=order.id,
            details=f"Rejected order #{order.id} (buyer_id={order.buyer_id})"
        )
        db.session.add(admin_log)

        db.session.commit()
        flash('Order has been rejected/cancelled.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting order: {str(e)}', 'error')

    cache.clear()
    return redirect(url_for('admin.orders'))


@admin_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('admin.orders'))

    if order.status not in ['pending', 'confirmed']:
        flash(f'Cannot cancel order with status \'{order.status}\'.', 'error')
        return redirect(url_for('admin.orders'))

    try:
        order.status = 'cancelled'
        order.cancelled_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        db.session.commit()

        car = Car.query.get(order.car_id)
        car_label = f"{car.year} {car.make} {car.model}" if car else "your listing"

        admin_log = AdminActionLog(
            admin_id=current_user.id,
            action="cancel_order",
            resource_type="Order",
            resource_id=order.id,
            details=f"Cancelled order #{order.id} (buyer_id={order.buyer_id})"
        )
        db.session.add(admin_log)

        db.session.commit()
        flash('Order has been cancelled.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling order: {str(e)}', 'error')

    cache.clear()
    return redirect(url_for('admin.orders'))


@admin_bp.route('/audit-logs')
@admin_bp.route('/audit-logs/page/<int:page>')
@login_required
@admin_required
def audit_logs(page=1):
    per_page = 50

    logs_query = db.session.query(
        AdminActionLog,
        User.name.label('admin_name')
    ).join(User, AdminActionLog.admin_id == User.id)\
     .order_by(AdminActionLog.created_at.desc())

    logs_paginated = logs_query.paginate(page=page, per_page=per_page, error_out=False)
    logs_list = []

    for log in logs_paginated.items:
        log_dict = {
            'id': log.AdminActionLog.id,
            'admin_name': log.admin_name,
            'action': log.AdminActionLog.action,
            'resource_type': log.AdminActionLog.resource_type,
            'resource_id': log.AdminActionLog.resource_id,
            'details': log.AdminActionLog.details,
            'created_at': log.AdminActionLog.created_at
        }
        logs_list.append(log_dict)

    return render_template("AdminAuditLogs.html",
                         logs=logs_list,
                         pagination=logs_paginated)


def record_admin_action(admin_id, action, resource_type, resource_id=None, details=None):
    try:
        log = AdminActionLog(
            admin_id=admin_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to record admin action {action} on {resource_type}: {str(e)}")
