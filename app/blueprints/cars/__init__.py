from flask import Blueprint

cars_bp = Blueprint('cars', __name__)

from . import routes