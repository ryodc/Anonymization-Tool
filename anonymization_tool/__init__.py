# anonymization_tool/__init__.py
from flask import Flask
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Define the directory paths
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'temp/uploads')
    ANONYMIZED_FOLDER = os.path.join(os.path.dirname(__file__), 'temp/anonymized')
    LOG_FOLDER = os.path.join(os.path.dirname(__file__), 'temp/logs')

    # Ensure the directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(ANONYMIZED_FOLDER, exist_ok=True)
    os.makedirs(LOG_FOLDER, exist_ok=True)

    # Add the directories to the app config
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['ANONYMIZED_FOLDER'] = ANONYMIZED_FOLDER
    app.config['LOG_FOLDER'] = LOG_FOLDER

    # Import and register the main blueprint
    from .routes import main
    app.register_blueprint(main)

    return app
