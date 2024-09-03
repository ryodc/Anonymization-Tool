# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'supersecretkey'
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_EXTENSIONS = {'xlsx', 'csv'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
