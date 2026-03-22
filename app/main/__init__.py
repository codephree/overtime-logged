from flask import Blueprint

# from datetime import date


bp = Blueprint('main', __name__)


from app.main import routes