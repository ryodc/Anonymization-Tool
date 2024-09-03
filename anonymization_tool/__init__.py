# anonymization_tool/__init__.py
from flask import Flask
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Import and register the main blueprint
    from .routes import main
    app.register_blueprint(main)

    return app
