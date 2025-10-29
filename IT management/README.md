# Flask Starter Project

## Setup

```bash
python -m venv venv
venv\Scripts\activate  # on Windows
pip install -r requirements.txt

# (Optional) copy env vars
copy .env.example .env
```

## Database setup

```bash
# Initialize migrations directory (run once)
flask db init

# Generate migration after model changes
flask db migrate -m "Initial tables"

# Apply migrations to the database
flask db upgrade
```

## Run

```bash
set FLASK_APP=wsgi.py  # on Windows cmd, use $env:FLASK_APP="wsgi.py" for PowerShell
python wsgi.py
```

Navigate to `http://127.0.0.1:5000` and you should see the starter page.
