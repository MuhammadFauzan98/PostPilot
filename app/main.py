from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, desc, func
from app import db
from app.models import User, Blog, Comment, Like, Bookmark
from app.utils import slugify, markdown_to_html, estimate_reading_time
from datetime import datetime, timezone

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # Featured blogs
    featured_blogs = Blog.query.filter_by(
        status='published', 
        featured=True
    ).order_by(desc(Blog.created_at)).limit(3).all()
    
    return render_template('index.html', 
                         featured_blogs=featured_blogs)

@bp.route('/recent-stories')
def recent_stories():
    page = request.args.get('page', 1, type=int)
    
    # Recent blogs
    recent_blogs = Blog.query.filter_by(
        status='published'
    ).order_by(desc(Blog.created_at)).paginate(
        page=page, per_page=12, error_out=False
    )
    
    return render_template('blog/recent_stories.html', 
                         recent_blogs=recent_blogs)

@bp.route('/popular-stories')
def popular_stories():
    page = request.args.get('page', 1, type=int)
    
    # Popular blogs (by views)
    popular_blogs = Blog.query.filter_by(
        status='published'
    ).order_by(desc(Blog.views)).paginate(
        page=page, per_page=12, error_out=False
    )
    
    return render_template('blog/popular_stories.html', 
                         popular_blogs=popular_blogs)

@bp.route('/blog/<slug>')
def blog(slug):
    blog = Blog.query.filter_by(slug=slug, status='published').first_or_404()
    
    # Increment views
    blog.views = (blog.views or 0) + 1
    db.session.commit()
    
    # Get related blogs
    related_blogs = Blog.query.filter(
        Blog.status == 'published',
        Blog.id != blog.id,
        Blog.tags.contains(blog.tags.split(',')[0]) if blog.tags else True
    ).limit(3).all()
    
    # Check if user liked/bookmarked
    is_liked = False
    is_bookmarked = False
    if current_user.is_authenticated:
        is_liked = Like.query.filter_by(
            blog_id=blog.id, 
            user_id=current_user.id
        ).first() is not None
        is_bookmarked = Bookmark.query.filter_by(
            blog_id=blog.id, 
            user_id=current_user.id
        ).first() is not None
    
    # Convert markdown to HTML
    blog.content_html = markdown_to_html(blog.content)
    
    return render_template('blog/blog.html', 
                         blog=blog,
                         related_blogs=related_blogs,
                         is_liked=is_liked,
                         is_bookmarked=is_bookmarked)

@bp.route('/dashboard')
@login_required
def dashboard():
    # User's blogs
    user_blogs = Blog.query.filter_by(
        author_id=current_user.id
    ).order_by(desc(Blog.updated_at)).all()
    
    # Stats
    total_blogs = len(user_blogs)
    published_blogs = len([b for b in user_blogs if b.status == 'published'])
    total_likes = sum(blog.likes.count() for blog in user_blogs)
    total_views = sum(blog.views for blog in user_blogs)
    
    # Bookmarks
    bookmarks = Bookmark.query.filter_by(
        user_id=current_user.id
    ).order_by(desc(Bookmark.created_at)).limit(10).all()
    
    return render_template('blog/dashboard.html',
                         user_blogs=user_blogs,
                         total_blogs=total_blogs,
                         published_blogs=published_blogs,
                         total_likes=total_likes,
                         total_views=total_views,
                         bookmarks=bookmarks)


@bp.route('/duplicate/<int:blog_id>', methods=['POST'])
@login_required
def duplicate(blog_id):
    # Allow authors to quickly duplicate a blog as a draft
    blog = Blog.query.filter_by(id=blog_id, author_id=current_user.id).first_or_404()

    # Generate a unique slug for the copied blog
    slug = slugify(blog.title)
    counter = 1
    original_slug = slug
    while Blog.query.filter_by(slug=slug).first():
        slug = f"{original_slug}-{counter}"
        counter += 1

    new_blog = Blog(
        title=f"{blog.title} (Copy)",
        slug=slug,
        content=blog.content,
        tags=blog.tags,
        author_id=current_user.id,
        status='draft',
        excerpt=blog.excerpt
    )

    db.session.add(new_blog)
    db.session.commit()

    flash('Draft copied. You can edit the copy now.', 'success')
    return redirect(url_for('main.editor', blog_id=new_blog.id))

@bp.route('/editor', methods=['GET', 'POST'])
@bp.route('/editor/<int:blog_id>', methods=['GET', 'POST'])
@login_required
def editor(blog_id=None):
    # All authenticated users can write and post
    
    blog = None
    if blog_id:
        blog = Blog.query.filter_by(
            id=blog_id, 
            author_id=current_user.id
        ).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags = request.form.get('tags', '').strip()
        status = request.form.get('status', 'draft')
        
        if not title or not content:
            flash('Title and content are required.', 'danger')
            return redirect(request.url)
        
        if blog:
            # Update existing blog
            blog.title = title
            blog.content = content
            blog.tags = tags
            blog.status = status
            blog.updated_at = datetime.now(timezone.utc)
            message = 'Blog updated successfully!'
        else:
            # Create new blog
            slug = slugify(title)
            counter = 1
            original_slug = slug
            
            while Blog.query.filter_by(slug=slug).first():
                slug = f"{original_slug}-{counter}"
                counter += 1
            
            blog = Blog(
                title=title,
                slug=slug,
                content=content,
                tags=tags,
                author_id=current_user.id,
                status=status,
                excerpt=content[:200] + '...' if len(content) > 200 else content
            )
            db.session.add(blog)
            message = 'Blog saved successfully!'
        
        db.session.commit()
        flash(message, 'success')
        
        if status == 'published':
            return redirect(url_for('main.blog', slug=blog.slug))
        else:
            return redirect(url_for('main.editor', blog_id=blog.id))
    
    return render_template('blog/editor.html', blog=blog)

@bp.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    # Get user's published blogs
    published_blogs = Blog.query.filter_by(
        author_id=user.id, 
        status='published'
    ).order_by(desc(Blog.created_at)).all()
    
    # Get user stats
    total_blogs = Blog.query.filter_by(author_id=user.id).count()
    total_likes = db.session.query(func.count(Like.id)).join(Blog).filter(
        Blog.author_id == user.id
    ).scalar() or 0
    
    return render_template('user/profile.html',
                         user=user,
                         published_blogs=published_blogs,
                         total_blogs=total_blogs,
                         total_likes=total_likes)

@bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    if not query:
        return redirect(url_for('main.index'))
    
    # Search in title, content, and tags
    search_results = Blog.query.filter(
        Blog.status == 'published',
        or_(
            Blog.title.ilike(f'%{query}%'),
            Blog.content.ilike(f'%{query}%'),
            Blog.tags.ilike(f'%{query}%')
        )
    ).order_by(desc(Blog.created_at)).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('search.html', 
                         query=query,
                         results=search_results)

@bp.route('/my-blogs')
@login_required
def my_blogs():
    page = request.args.get('page', 1, type=int)
    
    blogs = Blog.query.filter_by(
        author_id=current_user.id
    ).order_by(desc(Blog.updated_at)).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('blog/my_blogs.html', blogs=blogs)

@bp.route('/delete-blog/<int:blog_id>', methods=['POST'])
@login_required
def delete_blog(blog_id):
    blog = Blog.query.filter_by(
        id=blog_id,
        author_id=current_user.id
    ).first_or_404()
    
    db.session.delete(blog)
    db.session.commit()
    flash('Blog deleted successfully.', 'success')
    return redirect(url_for('main.my_blogs'))