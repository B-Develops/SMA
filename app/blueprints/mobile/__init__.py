from flask import Blueprint

mobile_bp = Blueprint("mobile", __name__, template_folder="mobile")

from . import routes
