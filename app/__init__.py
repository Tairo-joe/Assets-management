from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_required
import logging
import sys
from dotenv import load_dotenv

# Optional Flask-Mail import
try:
    from flask_mail import Mail
    MAIL_AVAILABLE = True
except ImportError:
    MAIL_AVAILABLE = False
    Mail = None


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "main.login"
mail = Mail() if MAIL_AVAILABLE else None

def create_app():
    """Flask application factory."""
    app = Flask(__name__)

    # Configurations
    load_dotenv()
    app.config.from_object("config.Config")

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Initialize mail only if available
    if mail:
        mail.init_app(app)

    # Debug logging to verify environment and mail availability
    logger = logging.getLogger("app.init")
    logger.setLevel(logging.INFO)
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"MAIL_AVAILABLE at import: {MAIL_AVAILABLE}")
    logger.info(f"Mail extension initialized: {bool(mail)}")

    # Blueprint registration
    from .routes import main as main_bp
    app.register_blueprint(main_bp)
    

    return app
