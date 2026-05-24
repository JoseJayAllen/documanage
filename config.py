# config.py - Configuration settings
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'oqaadms-dev-secret-key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB for video and large file support

    # FIXED: Hardcoded MySQL connection exactly as requested
    # IMPORTANT: Replace 'your_password' with your actual MySQL root password
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@localhost/documanage'

    # Optional: Echo SQL for debugging (set to True only when troubleshooting)
    SQLALCHEMY_ECHO = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-change-this'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}