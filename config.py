import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base application configuration."""
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    # Database configuration (SQLite for local, RDS MySQL ready)
    DB_PATH = os.path.join(BASE_DIR, 'csm_database.sqlite3')
    DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ASSIGNMENT_UPLOADS = os.path.join(UPLOAD_FOLDER, 'assignments')
    SUBMISSION_UPLOADS = os.path.join(UPLOAD_FOLDER, 'submissions')
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 Megabytes max request size
    
    # Allowed file extensions whitelist
    DEFAULT_ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'zip', 'txt', 'py', 'java', 'cpp', 'c', 'png', 'jpg', 'jpeg'}
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    
    # AWS S3 Settings (Future Cloud Deployment)
    USE_S3 = os.environ.get('USE_S3', 'False').lower() in ('true', '1', 't')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'csm-assignment-submissions')
    
    # Email settings (AWS SES / SMTP)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@college.edu')
