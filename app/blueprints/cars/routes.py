from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from ...models import User, Car, Order, SavedCar, Payment
from ... import db, bcrypt
from ...utils import send_order_confirmation_email, create_order_notification
from datetime import datetime
from sqlalchemy import text, func
import os
import json
from werkzeug.utils import secure_filename
import magic
from ...payment_utils import generate_payment_reference
from . import cars_bp


def _get_active_car_or_abort(car_id):
    car = Car.query.get_or_404(car_id)
    if car.status != 'active':
        flash("This car is no longer available for purchase.", "error")
        return None
    return car


def _require_complete_profile_or_abort():
    if not current_user.phone or not current_user.location:
        flash('Please complete your profile before placing an order. Add your phone number and location so the seller can reach you.', 'warning')
        return False
    return True


def cancel_pending_orders_for_car(car_id, cancelled_by_user_id=None):
    orders = Order.query.filter_by(car_id=car_id).filter(Order.status.in_(['pending', 'confirmed'])).all()
    for order in orders:
        order.status = 'cancelled'
        order.cancelled_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        try:
            buyer_label = order.buyer.name or order.buyer.email if order.buyer else f"Buyer #{order.buyer_id}"
            create_order_notification(
                user_id=order.buyer_id,
                order_id=order.id,
                event_type="order_cancelled",
                title="Order Cancelled",
                message=f"A listing you ordered has been marked as sold. Order #{order.id} has been cancelled.",
                link=f"/orders/{order.id}"
            )
        except Exception:
            pass
    db.session.commit()
    return len(orders)


# File upload settings
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_mime_type(file_stream):
    try:
        file_stream.seek(0)
        file_data = file_stream.read(2048)
        file_stream.seek(0)
        
        mime_type = magic.from_buffer(file_data, mime=True)
        
        allowed_mime_types = {
            'image/png',
            'image/jpeg',
            'image/gif',
            'image/webp'
        }
        
        return mime_type in allowed_mime_types
    except Exception:
        return False

def save_uploaded_image(file, car_id):
    if not file or file.filename == "":
        return None
    
    if not allowed_file(file.filename):
        return None
    
    if not validate_mime_type(file.stream):
        return None
    
    ext = file.filename.rsplit(".", 1)[1].lower()
    import time
    timestamp = int(time.time())
    filename = f"car_{car_id}_{timestamp}_{secure_filename(file.filename)}"
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    return f"uploads/{filename}"

@cars_bp.route("/list", methods=["GET", "POST"])
@login_required
def list_car():
    if request.method == "POST":
        make = request.form.get("make", "").strip()
        model = request.form.get("model", "").strip()
        year = request.form.get("year")
        price = request.form.get("price")
        mileage = request.form.get("mileage")
        condition = request.form.get("condition", "used")
        description = request.form.get("description", "").strip()
        
        if not make or not model or not price:
            flash("Make, model, and price are required", "error")
            return redirect(url_for("cars.list_car"))
        
        try:
            year = int(year) if year else None
            price = float(price)
            mileage = int(mileage) if mileage else None
        except ValueError:
            flash("Invalid number format for year, price, or mileage", "error")
            return redirect(url_for("cars.list_car"))
        
        current_year = datetime.utcnow().year
        if year is not None:
            if year < 1900 or year > current_year + 1:
                flash(f"Year must be between 1900 and {current_year + 1}.", "error")
                return redirect(url_for("cars.list_car"))
        
        if price <= 0:
            flash("Price must be greater than zero.", "error")
            return redirect(url_for("cars.list_car"))
        if price > 100000000:  # ₦100,000,000 maximum
            flash("Price cannot exceed ₦100,000,000.", "error")
            return redirect(url_for("cars.list_car"))
        
        result = db.session.execute(text("""
            INSERT INTO cars (seller_id, make, model, year, price, mileage, condition, description)
            VALUES (:seller_id, :make, :model, :year, :price, :mileage, :condition, :description)
            RETURNING id
        """), {
            'seller_id': current_user.id,
            'make': make,
            'model': model,
            'year': year,
            'price': price,
            'mileage': mileage,
            'condition': condition,
            'description': description
        })
        
        car_id = result.fetchone()[0]
        
        image_url = None
        if "image" in request.files:
            file = request.files["image"]
            image_url = save_uploaded_image(file, car_id)
        
        if image_url:
            db.session.execute(text("UPDATE cars SET image_url = :image_url WHERE id = :id"), 
                            {'image_url': image_url, 'id': car_id})
        else:
            db.session.execute(text("UPDATE cars SET image_url = :image_url WHERE id = :id"), 
                            {'image_url': f"Assets/images/{make}.png", 'id': car_id})
        
        db.session.commit()
        
        flash("Car listed successfully!", "success")
        return redirect(url_for("cars.browse_cars"))
    
    return render_template("dashboard/ListCars.html")

@cars_bp.route("/my-listings")
@login_required
def my_listings():
    listings = db.session.query(
        Car,
        func.count(Order.id).filter(Order.status == 'pending').label('order_count')
    ).outerjoin(Order, Car.id == Order.car_id).filter(
        Car.seller_id == current_user.id
    ).group_by(Car.id).order_by(Car.created_at.desc()).all()
    
    total = Car.query.filter_by(seller_id=current_user.id).count()
    active = Car.query.filter_by(seller_id=current_user.id, status='active').count()
    sold = Car.query.filter_by(seller_id=current_user.id, status='sold').count()
    
    stats = {"total": total, "active": active, "sold": sold}
    
    return render_template("dashboard/MyListings.html", listings=listings, stats=stats)


@cars_bp.route("/seller-orders")
@login_required
def seller_orders():
    orders = db.session.query(
        Order,
        Car.year, Car.make, Car.model, Car.image_url, Car.status.label('car_status'),
        User.name.label('buyer_name'), User.email.label('buyer_email')
    ).join(Car, Order.car_id == Car.id)\
     .outerjoin(User, Order.buyer_id == User.id)\
     .filter(Car.seller_id == current_user.id)\
     .order_by(Order.created_at.desc()).all()
    
    order_list = []
    for order, year, make, model, image_url, car_status, buyer_name, buyer_email in orders:
        payment = Payment.query.filter_by(order_id=order.id).order_by(Payment.created_at.desc()).first()
        order_list.append({
            'id': order.id,
            'year': year,
            'make': make,
            'model': model,
            'image_url': image_url,
            'car_status': car_status,
            'order_amount': order.order_amount,
            'listed_price': order.listed_price,
            'status': order.status,
            'payment_method': order.payment_method,
            'payment_status': payment.status if payment else None,
            'payment_reference': payment.provider_reference if payment else None,
            'buyer_name': buyer_name or 'Deleted User',
            'buyer_email': buyer_email or '',
            'delivery_address': order.delivery_address,
            'notes': order.notes,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M') if order.created_at else 'N/A',
        })
    
    pending_count = sum(1 for o in order_list if o['status'] == 'pending')
    confirmed_count = sum(1 for o in order_list if o['status'] == 'confirmed')
    completed_count = sum(1 for o in order_list if o['status'] == 'completed')
    
    stats = {
        'pending': pending_count,
        'confirmed': confirmed_count,
        'completed': completed_count,
        'total': len(order_list),
    }
    
    return render_template("dashboard/SellerOrders.html", orders=order_list, stats=stats)

@cars_bp.route("/cars/<int:car_id>/edit", methods=["GET", "POST"])
@login_required
def edit_car(car_id):
    car = Car.query.filter_by(id=car_id, seller_id=current_user.id).first()
    
    if not car:
        flash("Listing not found or access denied.", "error")
        return redirect(url_for("cars.my_listings"))
    
    if request.method == "POST":
        make = request.form.get("make", "").strip()
        model = request.form.get("model", "").strip()
        year = request.form.get("year")
        price = request.form.get("price")
        mileage = request.form.get("mileage")
        condition = request.form.get("condition", "used")
        description = request.form.get("description", "").strip()
        
        if not make or not model or not price:
            flash("Make, model, and price are required", "error")
            return redirect(url_for("cars.edit_car", car_id=car_id))
        
        try:
            year = int(year) if year else None
            price = float(price)
            mileage = int(mileage) if mileage else None
        except ValueError:
            flash("Invalid number format", "error")
            return redirect(url_for("cars.edit_car", car_id=car_id))
        
        current_year = datetime.utcnow().year
        if year is not None:
            if year < 1900 or year > current_year + 1:
                flash(f"Year must be between 1900 and {current_year + 1}.", "error")
                return redirect(url_for("cars.edit_car", car_id=car_id))
        
        if price <= 0:
            flash("Price must be greater than zero.", "error")
            return redirect(url_for("cars.edit_car", car_id=car_id))
        if price > 100000000:  # ₦100,000,000 maximum
            flash("Price cannot exceed ₦100,000,000.", "error")
            return redirect(url_for("cars.edit_car", car_id=car_id))
        
        image_url = car.image_url
        if "image" in request.files and request.files["image"].filename:
            file = request.files["image"]
            new_image = save_uploaded_image(file, car_id)
            if new_image:
                image_url = new_image
        
        car.make = make
        car.model = model
        car.year = year
        car.price = price
        car.mileage = mileage
        car.condition = condition
        car.description = description
        car.image_url = image_url
        
        db.session.commit()
        
        flash("Listing updated successfully!", "success")
        return redirect(url_for("cars.my_listings"))
    
    return render_template("dashboard/EditCar.html", car=car)

@cars_bp.route("/cars/<int:car_id>/delete", methods=["POST"])
@login_required
def delete_car(car_id):
    car = Car.query.filter_by(id=car_id, seller_id=current_user.id).first()
    
    if not car:
        flash("Listing not found or access denied.", "error")
        return redirect(url_for("cars.my_listings"))
    
    try:
        Order.query.filter_by(car_id=car_id).delete()
        SavedCar.query.filter_by(car_id=car_id).delete()
        db.session.delete(car)
        db.session.commit()
        flash("Listing deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting listing: {str(e)}", "error")
    
    return redirect(url_for("cars.my_listings"))

@cars_bp.route("/cars/<int:car_id>/mark-sold", methods=["POST"])
@login_required
def mark_car_sold(car_id):
    car = Car.query.filter_by(id=car_id, seller_id=current_user.id).first()

    if not car:
        flash("Listing not found or access denied.", "error")
        return redirect(url_for("cars.my_listings"))

    if car.status == 'sold':
        flash("This listing is already marked as sold.", "info")
        return redirect(url_for("cars.my_listings"))

    cancelled_count = cancel_pending_orders_for_car(car_id)
    car.status = 'sold'
    db.session.commit()

    if cancelled_count > 0:
        flash(f"Listing marked as sold. {cancelled_count} pending order(s) were cancelled and buyers were notified.", "success")
    else:
        flash("Listing marked as sold.", "success")
    return redirect(url_for("cars.my_listings"))

@cars_bp.route("/browse")
def browse_cars():
    query = Car.query.filter(Car.status == 'active')
    
    search_query = request.args.get('q', '').strip()
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Car.make.ilike(search_term),
                Car.model.ilike(search_term),
                Car.description.ilike(search_term)
            )
        )
    
    make_filter = request.args.get('make', '').strip()
    if make_filter:
        query = query.filter(Car.make == make_filter)
    
    condition_filter = request.args.get('condition', '').strip()
    if condition_filter:
        query = query.filter(Car.condition == condition_filter)
    
    min_price = request.args.get('min_price', '').strip()
    if min_price:
        try:
            min_price_float = float(min_price)
            query = query.filter(Car.price >= min_price_float)
        except ValueError:
            pass
    
    max_price = request.args.get('max_price', '').strip()
    if max_price:
        try:
            max_price_float = float(max_price)
            query = query.filter(Car.price <= max_price_float)
        except ValueError:
            pass
    
    min_year = request.args.get('min_year', '').strip()
    if min_year:
        try:
            min_year_int = int(min_year)
            query = query.filter(Car.year >= min_year_int)
        except ValueError:
            pass
    
    max_year = request.args.get('max_year', '').strip()
    if max_year:
        try:
            max_year_int = int(max_year)
            query = query.filter(Car.year <= max_year_int)
        except ValueError:
            pass
    
    sort_option = request.args.get('sort', 'newest').strip()
    if sort_option == 'price_low':
        query = query.order_by(Car.price.asc())
    elif sort_option == 'price_high':
        query = query.order_by(Car.price.desc())
    elif sort_option == 'mileage_low':
        query = query.order_by(Car.mileage.asc())
    elif sort_option == 'mileage_high':
        query = query.order_by(Car.mileage.desc())
    else:  # newest (default)
        query = query.order_by(Car.created_at.desc())
    
    cars = query.all()
    
    makes = db.session.query(Car.make.distinct()).filter(
        Car.status == 'active',
        Car.make.isnot(None)
    ).order_by(Car.make.asc()).all()
    
    current_filters = {
        'q': search_query,
        'make': make_filter,
        'condition': condition_filter,
        'min_price': min_price,
        'max_price': max_price,
        'min_year': min_year,
        'max_year': max_year,
        'sort': sort_option
    }
    
    return render_template(
        "BrowseCars.html", 
        cars=cars,
        makes=makes,
        filters=current_filters
    )

@cars_bp.route("/cars/<int:car_id>")
def car_detail(car_id):
    car = Car.query.get_or_404(car_id)
    seller = User.query.with_entities(User.name, User.phone, User.location).filter_by(id=car.seller_id).first()
    highest_bid = db.session.query(db.func.max(Order.order_amount)).filter_by(car_id=car_id, status='pending').first()
    return render_template("View-details.html", car=car, seller=seller, highest_bid=highest_bid)

@cars_bp.route("/cars/<int:car_id>/order", methods=["POST"])
@login_required
def place_order(car_id):
    order_amount = request.form.get("order_amount")
    payment_method = request.form.get("payment_method", "").strip()
    delivery_address = request.form.get("delivery_address", "").strip()
    notes = request.form.get("notes", "").strip()

    if not order_amount:
        flash("Order amount is required", "error")
        return redirect(url_for("cars.car_detail", car_id=car_id))

    try:
        order_amount_float = float(order_amount)
        if order_amount_float < 1000:
            flash("Order amount must be at least ₦1,000.", "error")
            return redirect(url_for("cars.car_detail", car_id=car_id))
        if order_amount_float > 100000000:
            flash("Order amount cannot exceed ₦100,000,000.", "error")
            return redirect(url_for("cars.car_detail", car_id=car_id))
    except ValueError:
        flash("Invalid order amount.", "error")
        return redirect(url_for("cars.car_detail", car_id=car_id))

    car = _get_active_car_or_abort(car_id)
    if car is None:
        return redirect(url_for("cars.car_detail", car_id=car_id))

    existing_order = Order.query.filter_by(
        buyer_id=current_user.id,
        car_id=car_id
    ).filter(Order.status.in_(['pending', 'confirmed'])).first()

    if existing_order:
        flash("You already have an order for this car.", "info")
        return redirect(url_for("dashboard"))

    if not _require_complete_profile_or_abort():
        return redirect(url_for('profiles.edit_profile'))

    try:
        listed_price_float = float(car.price)

        new_order = Order(
            buyer_id=current_user.id,
            car_id=car_id,
            order_amount=order_amount_float,
            listed_price=listed_price_float,
            payment_method=payment_method,
            delivery_address=delivery_address if delivery_address else None,
            notes=notes if notes else None,
            status='pending'
        )
        db.session.add(new_order)
        db.session.commit()

        payment = Payment(
            order_id=new_order.id,
            user_id=current_user.id,
            car_id=car_id,
            amount=order_amount_float,
            currency='NGN',
            provider='unset',
            provider_reference=generate_payment_reference(),
            status='pending',
            payment_data=json.dumps({
                'source': 'order_creation',
                'payment_method': payment_method,
            }),
        )
        db.session.add(payment)
        db.session.commit()

        buyer_label = current_user.name or current_user.email

        # Create in-app notification for the seller
        try:
            create_order_notification(
                user_id=car.seller_id,
                order_id=new_order.id,
                event_type="order_received",
                title="New Order Received",
                message=f"{buyer_label} placed an order of ₦{order_amount_float:,.0f} on your {car.year} {car.make} {car.model}.",
                link=f"/admin/orders"
            )
        except Exception:
            pass

        # Create in-app notification for the buyer
        try:
            create_order_notification(
                user_id=current_user.id,
                order_id=new_order.id,
                event_type="order_created",
                title="Order Placed",
                message=f"Your order for {car.year} {car.make} {car.model} has been placed successfully.",
                link=f"/orders/{new_order.id}"
            )
        except Exception:
            pass

        # Send confirmation email
        try:
            send_order_confirmation_email(
                user_email=current_user.email,
                user_name=current_user.name,
                order_id=new_order.id,
                car=car,
                order_amount=order_amount_float
            )
        except Exception:
            pass

        return redirect(url_for("cars.order_success", order_id=new_order.id))
    except Exception as e:
        db.session.rollback()
        flash(f"Error placing order: {str(e)}", "error")
        return redirect(url_for("cars.car_detail", car_id=car_id))

@cars_bp.route("/cars/<int:car_id>/save", methods=["POST"])
@login_required
def save_car(car_id):
    try:
        existing = SavedCar.query.filter_by(user_id=current_user.id, car_id=car_id).first()
        if not existing:
            new_saved_car = SavedCar(user_id=current_user.id, car_id=car_id)
            db.session.add(new_saved_car)
            db.session.commit()
            flash("Car saved to your favorites!", "success")
        else:
            flash("Car is already in your saved list!", "info")
    except Exception:
        db.session.rollback()
        flash("Car is already in your saved list!", "info")
    
    return redirect(url_for("dashboard"))

@cars_bp.route("/cars/<int:car_id>/unsave", methods=["POST"])
@login_required
def unsave_car(car_id):
    try:
        result = SavedCar.query.filter_by(user_id=current_user.id, car_id=car_id).delete()
        db.session.commit()
        
        if result > 0:
            flash("Car removed from saved list.", "info")
        else:
            flash("Car was not in your saved list.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"Error removing car from saved list: {str(e)}", "error")
    
    return redirect(url_for("dashboard"))

@cars_bp.route("/cars/<int:car_id>/review", methods=["POST"])
@login_required
def review_order_post(car_id):
    car = _get_active_car_or_abort(car_id)
    if car is None:
        return redirect(url_for("cars.car_detail", car_id=car_id))

    if not _require_complete_profile_or_abort():
        return redirect(url_for('profiles.edit_profile'))

    try:
        order_amount = float(request.form.get("order_amount", "") or car.price)
        if order_amount < 1000:
            flash("Order amount must be at least ₦1,000.", "error")
            return redirect(url_for("cars.car_detail", car_id=car_id))
    except (ValueError, TypeError):
        flash("Invalid order amount.", "error")
        return redirect(url_for("cars.car_detail", car_id=car_id))

    payment_method = request.form.get("payment_method", "").strip()
    if not payment_method:
        flash("Please select a payment method.", "error")
        return redirect(url_for("cars.car_detail", car_id=car_id))

    delivery_address = request.form.get("delivery_address", "").strip()
    notes = request.form.get("notes", "").strip()

    session_key = f"order_review_{current_user.id}_{car_id}"
    from flask import session
    session[session_key] = {
        "order_amount": order_amount,
        "payment_method": payment_method,
        "delivery_address": delivery_address,
        "notes": notes,
        "created_at": datetime.utcnow().isoformat(),
    }

    return redirect(url_for("cars.review_order_get", car_id=car_id))

@cars_bp.route("/cars/<int:car_id>/review")
@login_required
def review_order_get(car_id):
    car = Car.query.get_or_404(car_id)
    
    session_key = f"order_review_{current_user.id}_{car_id}"
    from flask import session
    payload = session.pop(session_key, None)
    
    if payload is None:
        flash("No order details found. Please fill out the order form again.", "info")
        return redirect(url_for("cars.car_detail", car_id=car_id))
    
    import datetime as _dt
    created_at = _dt.datetime.fromisoformat(payload["created_at"])
    if (_dt.datetime.utcnow() - created_at).total_seconds() > 1800:
        flash("Order review session expired. Please try again.", "info")
        return redirect(url_for("cars.car_detail", car_id=car_id))
    
    return render_template(
        "dashboard/OrderReview.html",
        car=car,
        order_amount=payload["order_amount"],
        payment_method=payload["payment_method"],
        delivery_address=payload["delivery_address"],
        notes=payload["notes"],
    )

@cars_bp.route("/cars/<int:car_id>/bid", methods=["POST"])
@login_required
def place_bid_redirect(car_id):
    flash("The bidding system has been replaced with orders. Please use the order form.", "info")
    return redirect(url_for("cars.car_detail", car_id=car_id))

@cars_bp.route("/order/<int:order_id>/success")
@login_required
def order_success(order_id):
    order = Order.query.filter_by(id=order_id, buyer_id=current_user.id).first()
    
    if not order:
        flash("Order not found", "error")
        return redirect(url_for("dashboard"))
    
    car = Car.query.get(order.car_id)
    if not car:
        flash("Car not found", "error")
        return redirect(url_for("dashboard"))
    
    return render_template(
        "dashboard/OrderSuccess.html",
        order=order,
        car=car
    )