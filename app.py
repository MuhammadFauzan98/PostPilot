import os
from dotenv import load_dotenv
from app import create_app

# Load environment variables from .env if present
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)