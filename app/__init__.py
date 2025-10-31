from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_required
import sqlalchemy as sa
import logging
import sys
import os
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
    # Load .env from project root reliably (../.env from this file)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    load_dotenv(os.path.join(base_dir, '.env'))
    app.config.from_object("config.Config")

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Initialize mail only if available
    if mail:
        mail.init_app(app)

    # Safety: ensure maintenance approval columns exist for SQLite deployments
    with app.app_context():
        try:
            engine = db.get_engine()
            url = str(engine.url)
            if url.startswith('sqlite:///'):
                with engine.connect() as conn:
                    cols = [r[1] for r in conn.exec_driver_sql('PRAGMA table_info(maintenance)').fetchall()]
                    to_add = []
                    if 'status' not in cols:
                        to_add.append("ALTER TABLE maintenance ADD COLUMN status VARCHAR(20)")
                    if 'approved_by' not in cols:
                        to_add.append("ALTER TABLE maintenance ADD COLUMN approved_by INTEGER")
                    if 'approved_at' not in cols:
                        to_add.append("ALTER TABLE maintenance ADD COLUMN approved_at DATETIME")
                    for stmt in to_add:
                        conn.exec_driver_sql(stmt)
        except Exception:
            # Non-fatal: migrations are still the canonical path
            pass

    # Debug logging to verify environment and mail availability
    logger = logging.getLogger("app.init")
    logger.setLevel(logging.INFO)
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"MAIL_AVAILABLE at import: {MAIL_AVAILABLE}")
    logger.info(f"Mail extension initialized: {bool(mail)}")

    # Blueprint registration
    from .routes import main as main_bp
    app.register_blueprint(main_bp)
    
    def format_ghs(value):
        try:
            val = float(value or 0)
        except Exception:
            return "GH₵0.00"
        return f"GH₵{val:,.2f}"
    app.jinja_env.filters['ghs'] = format_ghs

    return app
