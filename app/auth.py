from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from app import db, oauth
from app.models import User
from app.utils import slugify
import os
import json

bp = Blueprint('auth', __name__)


def _resolve_google_redirect():
    """Return a stable redirect URI for Google OAuth to avoid host mismatches."""
    # Highest priority: explicit override
    forced = current_app.config.get('GOOGLE_REDIRECT_URI')
    if forced:
        return forced

    # Next: SERVER_NAME if set (e.g., localhost:5000 or 127.0.0.1:5000)
    server_name = current_app.config.get('SERVER_NAME')
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme or 'http')
    if server_name:
        return f"{scheme}://{server_name}/auth/google-callback"

    # Then: actual host from the current request (matches how the user accessed the app)
    if request.host:
        return f"{scheme}://{request.host}/auth/google-callback"

    # Fallback: default to localhost:5000 to match common Google console config
    return f"{scheme}://localhost:5000/auth/google-callback"

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if not email or '@' not in email:
            errors.append('Valid email is required.')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        # Check existing user
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken.')
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        credential = request.form.get('credential', '').strip().lower()
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        # Try to find user by email or username
        user = User.query.filter(
            (User.email == credential) | (User.username == credential)
        ).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Logged in successfully!', 'success')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('auth/login.html')

@bp.route('/google-login')
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if not oauth._registry.get('google'):
        flash('Google login is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.', 'danger')
        return redirect(url_for('auth.login'))

    # Mark session as permanent and ensure it's initialized before OAuth redirect
    session.permanent = True
    current_app.permanent_session_lifetime = current_app.config['PERMANENT_SESSION_LIFETIME']
    # Force session to be created and ensure it's saved
    session['_oauth_init'] = True
    
    # Use the host from the current request to avoid host mismatches
    redirect_uri = _resolve_google_redirect()
    print(f"[OAuth] Initiating login from host: {request.host}, redirect_uri: {redirect_uri}")
    
    return oauth.google.authorize_redirect(redirect_uri)

@bp.route('/google-callback')
def google_callback():
    if not oauth._registry.get('google'):
        flash('Google login is not configured.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        # Get the authorization code from the callback
        code = request.args.get('code')
        state = request.args.get('state')
        
        print(f"[OAuth] Callback received - Code: {code[:20] if code else 'None'}..., State: {state[:20] if state else 'None'}...")
        print(f"[OAuth] Session ID: {request.cookies.get('session', 'NO_SESSION')[:20]}...")
        
        token = oauth.google.authorize_access_token()
        print(f"[OAuth] Token obtained successfully")
    except Exception as e:
        # Log the specific error to server console to diagnose state/redirect issues
        error_str = str(e)
        print(f"[OAuth] authorize_access_token failed: {error_str}")
        
        # Check for specific state mismatch error
        if 'state' in error_str.lower() or 'csrf' in error_str.lower():
            print(f"[OAuth] State mismatch detected - this is a session persistence issue")
            flash('Session expired. Please try logging in again.', 'warning')
        else:
            flash('Google authorization failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    # Fetch user info (OIDC)
    userinfo = token.get('userinfo')
    if not userinfo:
        # Fallback to userinfo endpoint
        try:
            resp = oauth.google.get('userinfo')
            userinfo = resp.json()
        except Exception:
            userinfo = None

    if not userinfo:
        flash('Unable to retrieve Google profile.', 'danger')
        return redirect(url_for('auth.login'))

    email = (userinfo.get('email') or '').lower()
    name = userinfo.get('name') or ''
    picture = userinfo.get('picture') or ''

    if not email:
        flash('Google account has no email.', 'danger')
        return redirect(url_for('auth.login'))

    # Existing user by email
    user = User.query.filter_by(email=email).first()
    if not user:
        # Create new user, derive username
        base_username = slugify(name) if name else (email.split('@')[0])
        username = base_username or f'user_{os.urandom(4).hex()}'

        # Ensure unique username
        original = username
        i = 1
        while User.query.filter_by(username=username).first():
            username = f"{original}{i}"
            i += 1

        user = User(username=username, email=email, avatar=picture)
        # Set a random password to satisfy non-null constraint
        user.set_password(os.urandom(16).hex())
        db.session.add(user)
        db.session.commit()

    login_user(user, remember=True)
    flash('Logged in with Google.', 'success')
    next_page = request.args.get('next')
    return redirect(next_page or url_for('main.index'))

@bp.route('/google/debug')
def google_debug():
    # Provide a simple JSON status for configuration
    cfg_id = os.environ.get('GOOGLE_CLIENT_ID') or ''
    cfg_secret = os.environ.get('GOOGLE_CLIENT_SECRET') or ''
    registered = bool(oauth._registry.get('google'))
    return {
        'google_oauth_registered': registered,
        'GOOGLE_CLIENT_ID_present': bool(cfg_id),
        'GOOGLE_CLIENT_SECRET_present': bool(cfg_secret),
        'redirect_uri_example': url_for('auth.google_callback', _external=True)
    }

@bp.route('/google/config', methods=['GET', 'POST'])
def google_config():
    # Enable configuration UI in debug mode, else restrict to admins
    debug_mode = current_app.debug
    if request.method == 'POST':
        client_id = request.form.get('client_id', '').strip()
        client_secret = request.form.get('client_secret', '').strip()
        if not client_id or not client_secret:
            flash('Client ID and Secret are required.', 'danger')
        else:
            # Persist to instance/google_oauth.json
            cfg_path = os.path.join(current_app.instance_path, 'google_oauth.json')
            try:
                os.makedirs(current_app.instance_path, exist_ok=True)
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'GOOGLE_CLIENT_ID': client_id,
                        'GOOGLE_CLIENT_SECRET': client_secret
                    }, f)
                # Update app config and re-register provider dynamically
                current_app.config['GOOGLE_CLIENT_ID'] = client_id
                current_app.config['GOOGLE_CLIENT_SECRET'] = client_secret
                # Replace existing provider if any
                oauth._registry.pop('google', None)
                oauth.register(
                    name='google',
                    client_id=client_id,
                    client_secret=client_secret,
                    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                    client_kwargs={'scope': 'openid email profile'}
                )
                flash('Google OAuth configured successfully.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                flash('Failed to save configuration.', 'danger')
    return render_template('auth/google_config.html', debug_mode=debug_mode)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))