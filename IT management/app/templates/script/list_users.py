import os
import sys

# Add project root to sys.path so 'import app' works when this script is nested under templates/
# Primary: 3 levels up (app/templates/script -> project root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
# Fallback: if not found, try 4 levels up
if not os.path.exists(os.path.join(PROJECT_ROOT, 'app', '__init__.py')):
    PROJECT_ROOT = os.path.abspath(os.path.join(PROJECT_ROOT, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app
from app.models import User

app = create_app()
with app.app_context():
    rows = [(u.id, u.username, u.role, u.email) for u in User.query.all()]
    if not rows:
        print("No users found.")
    else:
        print("Users (id, username, role, email):")
        for r in rows:
            print(r)
