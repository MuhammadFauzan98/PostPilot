import re
from datetime import datetime
from flask import current_app
import os
import markdown
from bleach import clean

def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text

def format_date(date, format='%B %d, %Y'):
    """Format datetime object to string."""
    if date is None:
        return ''
    return date.strftime(format)

def estimate_reading_time(content):
    """Estimate reading time in minutes."""
    words_per_minute = 200
    words = len(content.split())
    minutes = words // words_per_minute
    return max(1, minutes)

def excerpt(content, length=200):
    """Create excerpt from content."""
    if len(content) <= length:
        return content
    return content[:length].rsplit(' ', 1)[0] + '...'

def markdown_to_html(content):
    """Convert markdown to safe HTML."""
    html = markdown.markdown(content, extensions=['fenced_code', 'tables'])
    allowed_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 
                   'blockquote', 'code', 'pre', 'ul', 'ol', 'li', 'a', 'img', 
                   'br', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td']
    allowed_attrs = {
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'title']
    }
    return clean(html, tags=allowed_tags, attributes=allowed_attrs)

def is_allowed_file(filename):
    """Check if file extension is allowed."""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def avatar_static_path(user):
    """Return static-relative path for user's avatar with default fallback."""
    filename = (getattr(user, 'avatar', '') or '').strip()
    if not filename:
        return 'images/default_avatar.png'
    uploads_dir = current_app.config.get('UPLOAD_FOLDER')
    if uploads_dir:
        full_path = os.path.join(uploads_dir, filename)
        if os.path.isfile(full_path):
            return 'uploads/' + filename
    return 'images/default_avatar.png'

def _static_path_exists(rel_path: str) -> bool:
    """Check if a static-relative file exists on disk."""
    try:
        root = current_app.root_path
        static_dir = os.path.join(root, 'static')
        return os.path.isfile(os.path.join(static_dir, rel_path))
    except Exception:
        return False

def brand_logo_path() -> str:
    """Return universal brand logo path (SVG everywhere)."""
    return 'images/logo.svg'

def brand_title_image_path() -> str:
    """Return universal brand title image path (SVG everywhere)."""
    return 'images/logo.svg'