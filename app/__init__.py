from flask import Flask, request, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    
    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Ensure upload folder exists
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

    db.init_app(app)
    login_manager.init_app(app)
    
    from app.models import User, Blog, Comment, Like, Bookmark
    
    @app.before_request
    def before_request():
        g.user = current_user
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create tables
    with app.app_context():
        db.create_all()

    # Expose helpers to Jinja globals
    from app.utils import avatar_static_path, brand_logo_path, brand_title_image_path
    app.jinja_env.globals['avatar_url'] = avatar_static_path
    app.jinja_env.globals['brand_logo_url'] = brand_logo_path
    app.jinja_env.globals['brand_title_image_url'] = brand_title_image_path
    
    # Context processors
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)
    
    @app.context_processor
    def utility_processor():
        from app.utils import format_date, estimate_reading_time, excerpt, avatar_static_path, brand_logo_path, brand_title_image_path
        # avatar_url returns static-relative path with default fallback
        return dict(
            format_date=format_date,
            estimate_reading_time=estimate_reading_time,
            excerpt=excerpt,
            avatar_url=avatar_static_path,
            brand_logo_url=brand_logo_path,
            brand_title_image_url=brand_title_image_path
        )

    # OAuth availability flag for templates
    @app.context_processor
    def oauth_processor():
        available = bool(oauth._registry.get('google'))
        return dict(google_oauth_enabled=available)
    
    return app