from flask import Blueprint
from .auth.routes import auth_bp
from .user.stats.routes import stats_bp
from .user.orders.routes import orders_bp
from .user.payments.routes import payments_bp
from .user.interactions.routes import interactions_bp
from .user.profile.routes import profile_bp
from .user.options.routes import options_bp
from .admin import register_admin_apis
from .employee import register_employee_apis
from .landing import landing_bp

def init_apis(app):
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    
    # Auth APIs
    api_bp.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Landing APIs (Public)
    api_bp.register_blueprint(landing_bp, url_prefix='/landing')
    
    # User APIs
    api_bp.register_blueprint(stats_bp, url_prefix='/user')
    api_bp.register_blueprint(orders_bp, url_prefix='/user')
    api_bp.register_blueprint(payments_bp, url_prefix='/user/payments')
    api_bp.register_blueprint(interactions_bp, url_prefix='/user')
    api_bp.register_blueprint(profile_bp, url_prefix='/user')
    api_bp.register_blueprint(options_bp, url_prefix='/user/options')
    
    # Admin APIs
    admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
    register_admin_apis(admin_bp)
    api_bp.register_blueprint(admin_bp)

    # Employee APIs
    employee_bp = Blueprint('employee', __name__, url_prefix='/employee')
    register_employee_apis(employee_bp)
    api_bp.register_blueprint(employee_bp)
    
    app.register_blueprint(api_bp)
