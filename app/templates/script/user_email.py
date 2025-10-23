import os
import sys

# Add project root to sys.path so 'import app' works when this script is nested under templates/
# Primary: 3 levels up (app/templates/script -> project root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
# Fallback: if not found, try 4 levels up (in case script moves one level deeper)
if not os.path.exists(os.path.join(PROJECT_ROOT, 'app', '__init__.py')):
    PROJECT_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # Update existing Admin
    u = User.query.filter_by(username='admin').first()
    if u:
        u.email = 'cudjoetairo@gmail.com'  # real address
        db.session.commit()
        print(f"Updated admin email to: {u.email}")
    else:
        print("Admin user 'admin' not found")

    # Update existing IT
    it = User.query.filter_by(username='ituser').first()
    if it:
        it.email = 'pappygenius@gmail.com'
        db.session.commit()
        print(f"Updated ituser email to: {it.email}")
    else:
        print("IT user 'ituser' not found")