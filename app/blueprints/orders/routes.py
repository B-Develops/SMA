from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from ...models import User, Car, Order
from ... import db, cache
from sqlalchemy.orm import joinedload
from datetime import datetime
from . import orders_bp

@orders_bp.route('/my-orders')
@login_required
@cache.cached(timeout=60, key_prefix='my_orders')
def my_orders():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    user_id = current_user.id
    orders_pagination = Order.query.options(joinedload(Order.car), joinedload(Order.payments))\
        .filter_by(buyer_id=user_id)\
        .order_by(Order.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('MyOrders.html',
                         orders=orders_pagination.items,
                         pagination=orders_pagination)

@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Cancel a user's order."""
    order = Order.query.filter_by(id=order_id, buyer_id=current_user.id).first()
    
    if not order:
        flash('Order not found or access denied.', 'error')
        return redirect(url_for('orders.my_orders'))
    
    # Only allow cancellation of pending or confirmed orders
    if order.status not in ['pending', 'confirmed']:
        flash('Only pending or confirmed orders can be cancelled.', 'error')
        return redirect(url_for('orders.my_orders'))
    
    try:
        order.status = 'cancelled'
        order.cancelled_at = datetime.utcnow()
        db.session.commit()
        
        flash('Order cancelled successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling order: {str(e)}', 'error')
    
    return redirect(url_for('orders.my_orders'))

@orders_bp.route('/<int:order_id>')
@login_required
def view_order(order_id):
    order = Order.query.options(joinedload(Order.car))\
        .filter_by(id=order_id, buyer_id=current_user.id).first()
    if not order:
        flash('Order not found or access denied.', 'error')
        return redirect(url_for('orders.my_orders'))
    car = order.car
    return render_template('dashboard/OrderSuccess.html',
                         order=order,
                         car=car,
                         detail_view=True)