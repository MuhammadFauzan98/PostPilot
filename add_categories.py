from app import create_app
from database import db, Category

def add_categories():
    app = create_app()
    with app.app_context():
        # Check if categories already exist
        if Category.query.first() is not None:
            print("Categories already exist.")
            return

        categories = [
            {'name': 'Technology', 'slug': 'technology', 'description': 'Latest tech news and trends.'},
            {'name': 'Lifestyle', 'slug': 'lifestyle', 'description': 'Lifestyle tips and stories.'},
            {'name': 'Travel', 'slug': 'travel', 'description': 'Travel guides and experiences.'},
            {'name': 'Food', 'slug': 'food', 'description': 'Delicious recipes and food reviews.'},
            {'name': 'Health', 'slug': 'health', 'description': 'Health and wellness advice.'},
            {'name': 'Business', 'slug': 'business', 'description': 'Business insights and analysis.'},
            {'name': 'Entertainment', 'slug': 'entertainment', 'description': 'Movies, music, and more.'},
            {'name': 'Education', 'slug': 'education', 'description': 'Educational content and resources.'}
        ]

        for cat_data in categories:
            category = Category(**cat_data)
            db.session.add(category)

        db.session.commit()
        print("Categories added successfully.")

if __name__ == '__main__':
    add_categories()
