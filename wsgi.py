# wsgi.py
from app import create_app

# Create the Flask application instance
app = create_app()

# This allows Gunicorn to access the application
if __name__ == "__main__":
    app.run() 