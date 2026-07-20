from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user, logout_user
from ...models import User, Car, SavedCar, Notification, NotificationSettings, Order, AdminActionLog
from ... import db
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from . import profiles_bp

@profiles_bp.route('/profile')
@login_required
def view_profile():
    user = User.query.get(current_user.id)

    settings = NotificationSettings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = NotificationSettings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()

    stats = {
        'total_orders': Order.query.filter_by(buyer_id=current_user.id).count(),
        'pending_orders': Order.query.filter_by(buyer_id=current_user.id, status='pending').count(),
        'saved_cars': SavedCar.query.filter_by(user_id=current_user.id).count(),
    }

    return render_template('Profile.html', profile=user, notification_settings=settings, stats=stats)

@profiles_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = User.query.get(current_user.id)
    if request.method == 'POST':
        user.name = request.form.get('name', user.name)
        user.phone = request.form.get('phone', user.phone)
        user.location = request.form.get('location', user.location)
        user.bio = request.form.get('bio', user.bio)
        
        avatar = request.files.get('avatar')
        if avatar and avatar.filename:
            filename = secure_filename(avatar.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            avatar.save(filepath)
            user.avatar_url = f"uploads/{filename}"
        
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profiles.view_profile'))
    return render_template('dashboard/EditProfile.html', profile=user)

@profiles_bp.route('/settings')
@login_required
def settings():
    user = User.query.get(current_user.id)
    return render_template('Settings.html', user=user)

@profiles_bp.route('/settings/password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        from ... import bcrypt
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        user = User.query.get(current_user.id)
        if not bcrypt.check_password_hash(user.password, current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('profiles.change_password'))
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('profiles.change_password'))
        if len(new_password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return redirect(url_for('profiles.change_password'))
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('profiles.settings'))
    return render_template('dashboard/ChangePassword.html')

@profiles_bp.route('/settings/notifications', methods=['GET', 'POST'])
@login_required
def notification_settings():
    settings = NotificationSettings.query.filter_by(user_id=current_user.id).first()
    if not settings:
        settings = NotificationSettings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()
    if request.method == 'POST':
        settings.email_order_notifications = 1 if request.form.get('email_order_notifications') else 0
        settings.email_message_notifications = 1 if request.form.get('email_message_notifications') else 0
        settings.email_order_accepted = 1 if request.form.get('email_order_accepted') else 0
        settings.email_price_drop = 1 if request.form.get('email_price_drop') else 0
        settings.push_new_orders = 1 if request.form.get('push_new_orders') else 0
        settings.push_messages = 1 if request.form.get('push_messages') else 0
        settings.push_order_accepted = 1 if request.form.get('push_order_accepted') else 0
        settings.in_app_notifications = 1 if request.form.get('in_app_notifications') else 0
        db.session.commit()
        flash('Notification settings updated.', 'success')
        return redirect(url_for('profiles.notification_settings'))
    return render_template('dashboard/NotificationSettings.html', settings=settings)

@profiles_bp.route('/settings/delete-account', methods=['POST'])
@login_required
def delete_account():
    user = User.query.get(current_user.id)
    if user:
        user.name = 'Deleted User'
        user.email = f"deleted_{user.id}@anonymized.local"
        user.password = 'DELETED'
        user.phone = None
        user.location = None
        user.bio = None
        user.email_verified = 0
        user.phone_verified = 0
        user.id_verified = 0
        user.address_verified = 0
        user.updated_at = datetime.utcnow()

        Order.query.filter_by(buyer_id=user.id).delete()
        SavedCar.query.filter_by(user_id=user.id).delete()
        NotificationSettings.query.filter_by(user_id=user.id).delete()

        db.session.add(AdminActionLog(
            admin_id=current_user.id,
            action="user_deleted_self",
            resource_type="User",
            resource_id=user.id,
            details=f"User {user.email} anonymized their own account"
        ))
        db.session.commit()

        logout_user()
        flash('Your account has been anonymized and you have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@profiles_bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=0).count()
    return render_template('dashboard/Notifications.html',
                         notifications=notifications.items,
                         pagination=notifications,
                         unread_count=unread_count)

@profiles_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if notif:
        notif.is_read = 1
        db.session.commit()
    return redirect(url_for('profiles.notifications'))

@profiles_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=0).update({'is_read': 1})
    db.session.commit()
    return redirect(url_for('profiles.notifications'))

@profiles_bp.route('/notifications/delete/<int:notif_id>', methods=['POST'])
@login_required
def delete_notification(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if notif:
        db.session.delete(notif)
        db.session.commit()
    return redirect(url_for('profiles.notifications'))

@profiles_bp.route('/messages')
@login_required
def messages():
    return render_template('dashboard/Messages.html')

@profiles_bp.route('/saved-cars')
@login_required
def saved_cars():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    saved_cars_pagination = db.session.query(Car)\
        .join(SavedCar, Car.id == SavedCar.car_id)\
        .filter(SavedCar.user_id == current_user.id)\
        .order_by(SavedCar.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    saved_car_map = {sc.car_id: sc for sc in SavedCar.query.filter_by(user_id=current_user.id).all()}
    return render_template('saved_cars.html',
                         saved_cars=saved_cars_pagination.items,
                         saved_car_map=saved_car_map,
                         pagination=saved_cars_pagination)

@profiles_bp.route('/about')
def about():
    return render_template('about.html')

@profiles_bp.route('/help')
def help():
    return render_template('dashboard/Help.html')
