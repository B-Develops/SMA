from flask import render_template, request
from flask_login import login_required, current_user
from app.models import Car
from app import db
from . import mobile_bp


@mobile_bp.route("/browse-cars")
def browse_cars():
    query = request.args.get("q", "").strip()
    make = request.args.get("make", "").strip()
    condition = request.args.get("condition", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    sort = request.args.get("sort", "newest").strip()

    cars_query = Car.query.filter_by(status="active")

    if query:
        search = f"%{query}%"
        cars_query = cars_query.filter(
            db.or_(
                Car.make.ilike(search),
                Car.model.ilike(search),
                (Car.year.cast(db.String).ilike(search)),
            )
        )

    if make:
        cars_query = cars_query.filter(Car.make == make)
    if condition:
        cars_query = cars_query.filter(Car.condition == condition)
    if min_price.isdigit():
        cars_query = cars_query.filter(Car.price >= int(min_price))
    if max_price.isdigit():
        cars_query = cars_query.filter(Car.price <= int(max_price))

    if sort == "price_low":
        cars_query = cars_query.order_by(Car.price.asc())
    elif sort == "price_high":
        cars_query = cars_query.order_by(Car.price.desc())
    elif sort == "mileage_low":
        cars_query = cars_query.order_by(Car.mileage.asc())
    elif sort == "mileage_high":
        cars_query = cars_query.order_by(Car.mileage.desc())
    else:
        cars_query = cars_query.order_by(Car.created_at.desc())

    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = cars_query.paginate(page=page, per_page=per_page)
    cars = pagination.items

    makes = (
        db.session.query(Car.make, db.func.count(Car.id))
        .filter_by(status="active")
        .group_by(Car.make)
        .order_by(Car.make)
        .all()
    )

    filters = {
        "q": query,
        "make": make,
        "condition": condition,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
    }

    return render_template(
        "mobile/BrowseCars.html",
        cars=cars,
        makes=makes,
        filters=filters,
        pagination=pagination,
    )
