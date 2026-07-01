from flask import Blueprint

profiles_bp = Blueprint('profiles', __name__)

from . import routes