from flask import Flask
from api.routes import api
from config.config import Config
from services.loader_startup import initialize_and_index_all_sources


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api, url_prefix='/api')
    
    with app.app_context():
        initialize_and_index_all_sources()
        
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True) 