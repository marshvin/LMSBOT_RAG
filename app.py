from flask import Flask
from api.routes import api
from config.config import Config

def create_app():
    app = Flask(__name__)
    app.register_blueprint(api, url_prefix='/api')
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True) 