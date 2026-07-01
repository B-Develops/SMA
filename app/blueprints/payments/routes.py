from datetime import datetime
import json

from flask import flash, redirect, render_template, url_for, abort
from flask_login import current_user, login_required

from ... import db
from ...models import AdminActionLog, Order, Payment
from ...payment_utils import generate_payment_reference
from . import payments_bp


def get_or_create_payment(order):
    payment = Payment.query.filter_by(order_id=order.id).order_by(Payment.created_at.desc()).first()
    if payment:
        return payment

    payment = Payment(
        order_id=order.id,
        user_id=order.buyer_id,
        car_id=order.car_id,
        amount=order.order_amount,
        currency='NGN',
        provider='unset',
        provider_reference=generate_payment_reference(),
        status='pending',
        payment_data=json.dumps({
            'source': 'payment_scaffold',
            'payment_method': order.payment_method,
        }),
    )
    db.session.add(payment)
    db.session.commit()
    return payment


@payments_bp.route('/payments/<int:order_id>')
@login_required
def payment_page(order_id):
    order = Order.query.filter_by(id=order_id, buyer_id=current_user.id).first()
    if not order:
        abort(404)

    payment = get_or_create_payment(order)
    car = order.car

    return render_template(
        'payments/Payment.html',
        order=order,
        car=car,
        payment=payment,
    )


@payments_bp.route('/payments/<int:order_id>/initialize', methods=['POST'])
@login_required
def initialize_payment(order_id):
    order = Order.query.filter_by(id=order_id, buyer_id=current_user.id).first()
    if not order:
        abort(404)

    if order.status != 'confirmed':
        flash('This order must be accepted by admin before payment can start.', 'warning')
        return redirect(url_for('payments.payment_page', order_id=order.id))

    payment = get_or_create_payment(order)
    if payment.status == 'paid':
        flash('This order has already been paid.', 'success')
        return redirect(url_for('payments.payment_page', order_id=order.id))

    payment.provider = 'unset'
    payment.provider_reference = payment.provider_reference or generate_payment_reference()
    payment.status = 'pending'
    payment.payment_data = json.dumps({
        'source': 'payment_scaffold',
        'payment_method': order.payment_method,
        'ready_for_provider': True,
    })
    payment.updated_at = datetime.utcnow()
    db.session.commit()

    flash('Payment record is ready. Connect a provider to this route when available.', 'info')
    return redirect(url_for('payments.payment_page', order_id=order.id))


@payments_bp.route('/admin/payments/<int:payment_id>/mark-paid', methods=['POST'])
@login_required
def admin_mark_payment_paid(payment_id):
    if current_user.role != 'admin':
        abort(403)

    payment = Payment.query.get_or_404(payment_id)
    order = payment.order
    car = order.car

    if payment.status == 'paid':
        flash('This payment has already been marked as paid.', 'info')
        return redirect(url_for('admin.orders'))

    payment.status = 'paid'
    payment.paid_at = datetime.utcnow()
    payment.updated_at = datetime.utcnow()

    order.status = 'completed'
    order.completed_at = datetime.utcnow()
    order.updated_at = datetime.utcnow()

    if car and car.status != 'sold':
        car.status = 'sold'

    db.session.add(AdminActionLog(
        admin_id=current_user.id,
        action='mark_payment_paid',
        resource_type='Payment',
        resource_id=payment.id,
        details=f'Marked payment #{payment.id} for order #{order.id} as paid.',
    ))
    db.session.commit()

    flash('Payment marked as paid and order completed.', 'success')
    return redirect(url_for('admin.orders'))
