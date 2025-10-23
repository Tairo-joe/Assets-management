import os

class Config:
    """Base configuration."""

    # Change this in production!
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///site.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Notification settings
    LICENSE_EXPIRY_DAYS = int(os.getenv('LICENSE_EXPIRY_DAYS', '30'))
    WARRANTY_EXPIRY_DAYS = int(os.getenv('WARRANTY_EXPIRY_DAYS', '30'))
    
    # HR Integration settings
    HR_API_KEY = os.getenv('HR_API_KEY', 'hr-integration-key-123')
    HR_WEBHOOK_SECRET = os.getenv('HR_WEBHOOK_SECRET', 'webhook-secret-456')
    HR_SYSTEM_URL = os.getenv('HR_SYSTEM_URL', 'http://localhost:3000')
