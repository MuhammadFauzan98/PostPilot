from flask import Flask, request, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from config import Config
import os
import json
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
oauth = OAuth()

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
    
    # Allow http redirect URIs in development (Flask 2.3+: no app.env)
    env_name = str(app.config.get('ENV', os.getenv('FLASK_ENV', 'production'))).lower()
    if app.debug or env_name == 'development':
        os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')

    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)
    
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

    # Try loading Google OAuth config from instance/google_oauth.json if env missing
    if not (app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET')):
        cfg_path = os.path.join(app.instance_path, 'google_oauth.json')
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                app.config['GOOGLE_CLIENT_ID'] = cfg.get('GOOGLE_CLIENT_ID', '')
                app.config['GOOGLE_CLIENT_SECRET'] = cfg.get('GOOGLE_CLIENT_SECRET', '')
                print(f"[OAuth] Loaded Google credentials from {cfg_path}.")
        except Exception:
            pass

    # Register Google OAuth provider
    if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
        print('[OAuth] Google provider registered.')
    else:
        print('[OAuth] Google provider NOT registered. Missing GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET.')

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