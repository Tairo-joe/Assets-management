from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Employee")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120))
    contact = db.Column(db.String(120))
    assets = db.relationship("Asset", backref="employee", lazy=True)

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(64), unique=True, nullable=False)
    asset_type = db.Column(db.String(120))
    brand = db.Column(db.String(120))
    model = db.Column(db.String(120))
    serial_no = db.Column(db.String(120))
    purchase_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    status = db.Column(db.String(50))
    notes = db.Column(db.Text)
    assigned_to = db.Column(db.Integer, db.ForeignKey("employee.id"))
    maintenances = db.relationship("Maintenance", backref="asset", lazy=True)

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    date = db.Column(db.Date, default=datetime.utcnow)
    description = db.Column(db.Text)
    cost = db.Column(db.Float)
    status = db.Column(db.String(20), default="Pending")
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

class SoftwareLicense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    software_name = db.Column(db.String(120))
    license_key = db.Column(db.String(120))
    expiry_date = db.Column(db.Date)
    assigned_to = db.Column(db.Integer, db.ForeignKey("employee.id"))
