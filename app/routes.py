from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, current_app
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, Asset, Employee, Maintenance, SoftwareLicense
from . import db, mail, MAIL_AVAILABLE
import csv
from io import StringIO, BytesIO

# Optional imports
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

if MAIL_AVAILABLE:
    from flask_mail import Message

main = Blueprint("main", __name__)

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("main.login"))
            if current_user.role not in roles:
                flash("Access denied", "danger")
                return redirect(url_for("main.dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator

@main.route("/")
def index():
    return redirect(url_for("main.dashboard"))

@main.route("/dashboard", endpoint="dashboard")
@login_required
def dashboard():
    """Generic dashboard route that redirects to role-specific dashboard"""
    # Redirect to appropriate dashboard based on user role
    role_dashboards = {
        "Admin": "main.admin_dashboard",
        "IT": "main.it_dashboard",
        "Manager": "main.manager_dashboard",
        "Employee": "main.employee_dashboard",
    }
    return redirect(url_for(role_dashboards.get(current_user.role, "main.employee_dashboard")))

# -------------------- Authentication --------------------
@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        want_admin = bool(request.form.get("is_admin"))
        admin_code = request.form.get("admin_code", "").strip()
        if not username or not email or not password:
            flash("All fields are required", "warning")
            return redirect(url_for("main.register"))
        if len(password) < 8:
            flash("Password must be at least 8 characters", "warning")
            return redirect(url_for("main.register"))
        if User.query.filter((User.username == username)|(User.email==email)).first():
            flash("User already exists", "danger")
            return redirect(url_for("main.register"))
        role = "Employee"
        if want_admin:
            configured = current_app.config.get("ADMIN_REGISTRATION_CODE")
            if not configured:
                flash("Admin registration code not configured", "danger")
                return redirect(url_for("main.register"))
            if admin_code != configured:
                flash("Invalid admin registration code", "danger")
                return redirect(url_for("main.register"))
            role = "Admin"
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully, please login", "success")
        return redirect(url_for("main.login"))
    return render_template("auth/register.html")

@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        
        if not user:
            flash("Invalid username - User not found", "danger")
        elif not user.check_password(password):
            flash("Invalid password - Please try again", "danger")
        else:
            login_user(user)
            return redirect(url_for("main.dashboard"))
            
        return redirect(url_for("main.login"))
    return render_template("auth/login.html")

@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("main.login"))

# -------------------- Account / Password --------------------
@main.route("/account/change-password", methods=["GET", "POST"], endpoint="change_password")
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_user.check_password(current_password):
            flash("Current password is incorrect", "danger")
            return redirect(url_for("main.change_password"))

        if not new_password or len(new_password) < 8:
            flash("New password must be at least 8 characters", "warning")
            return redirect(url_for("main.change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match", "warning")
            return redirect(url_for("main.change_password"))

        current_user.set_password(new_password)
        db.session.commit()
        flash("Password updated successfully", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("auth/change_password.html")

# -------------------- Dashboards --------------------
@main.route("/admin/dashboard")
@login_required
@role_required("Admin")
def admin_dashboard():
    total_assets = Asset.query.count()
    total_employees = Employee.query.count()
    total_licenses = SoftwareLicense.query.count()
    maintenance_count = Maintenance.query.count()
    pending_maintenances = Maintenance.query.filter_by(status='Pending').order_by(Maintenance.date.desc()).limit(5).all()
    recent_approved = Maintenance.query.filter_by(status='Approved').order_by(Maintenance.approved_at.desc()).limit(5).all()
    
    # Asset distribution by type
    asset_types = []
    asset_counts = []
    from sqlalchemy import func
    asset_data = db.session.query(Asset.asset_type, func.count(Asset.id)).group_by(Asset.asset_type).all()
    for asset_type, count in asset_data:
        asset_types.append(asset_type or 'Unknown')
        asset_counts.append(count)
    
    # Monthly maintenance cost
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_costs = [0] * 12
    maintenance_records = Maintenance.query.all()
    for record in maintenance_records:
        if record.date:
            month = record.date.month - 1  # 0-indexed
            monthly_costs[month] += record.cost or 0
    
    return render_template("dashboards/admin.html", **locals())

@main.route("/admin/users")
@login_required
@role_required("Admin")
def admin_users():
    users = User.query.order_by(User.id.asc()).all()
    return render_template("users/manage.html", users=users)

@main.route("/admin/users/<int:user_id>/role", methods=["POST"])
@login_required
@role_required("Admin")
def admin_user_set_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role", "Employee")
    if new_role not in ["Admin", "IT", "Manager", "Employee"]:
        flash("Invalid role", "danger")
        return redirect(url_for("main.admin_users"))
    user.role = new_role
    db.session.commit()
    flash("User role updated", "success")
    return redirect(url_for("main.admin_users"))

@main.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@role_required("Admin")
def admin_user_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password", "")
    if len(new_password) < 8:
        flash("Password must be at least 8 characters", "warning")
        return redirect(url_for("main.admin_users"))
    user.set_password(new_password)
    db.session.commit()
    flash("Password reset successfully", "success")
    return redirect(url_for("main.admin_users"))

@main.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required("Admin")
def admin_user_delete(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own account", "warning")
        return redirect(url_for("main.admin_users"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted", "info")
    return redirect(url_for("main.admin_users"))

@main.route("/it/dashboard")
@login_required
@role_required("Admin", "IT")
def it_dashboard():
    pending_maintenance = Maintenance.query.order_by(Maintenance.date.desc()).limit(5).all()
    assets_repair = Asset.query.filter_by(status="Repair").count()
    licenses_expiring = SoftwareLicense.query.order_by(SoftwareLicense.expiry_date).limit(5).all()
    
    # License expiry by month
    expiry_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    expiry_counts = [0] * 12
    from datetime import date
    licenses = SoftwareLicense.query.filter(SoftwareLicense.expiry_date >= date.today()).all()
    for lic in licenses:
        if lic.expiry_date:
            month = lic.expiry_date.month - 1  # 0-indexed
            expiry_counts[month] += 1
    
    # Monthly maintenance cost
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_costs = [0] * 12
    maintenance_records = Maintenance.query.all()
    for record in maintenance_records:
        if record.date:
            month = record.date.month - 1  # 0-indexed
            monthly_costs[month] += record.cost or 0
    
    return render_template("dashboards/it.html", **locals())

@main.route("/manager/dashboard")
@login_required
@role_required("Admin", "Manager")
def manager_dashboard():
    total_assets = Asset.query.count()
    maintenance_cost = db.session.query(db.func.sum(Maintenance.cost)).scalar() or 0
    licenses_expiring = SoftwareLicense.query.order_by(SoftwareLicense.expiry_date).limit(5).all()
    warranties_expiring = Asset.query.order_by(Asset.warranty_expiry).limit(5).all()
    active_licenses = SoftwareLicense.query.count()
    
    # Asset status distribution
    status_labels = []
    status_counts = []
    from sqlalchemy import func
    status_data = db.session.query(Asset.status, func.count(Asset.id)).group_by(Asset.status).all()
    for status, count in status_data:
        status_labels.append(status or 'Unknown')
        status_counts.append(count)
    
    return render_template("dashboards/manager.html", **locals())

@main.route("/employee/dashboard")
@login_required
@role_required("Admin", "Employee")
def employee_dashboard():
    my_assets = Asset.query.filter_by(assigned_to=current_user.id).all()
    return render_template("dashboards/employee.html", **locals())

# -------------------- HR Integration Dashboard --------------------

# -------------------- Employees / Maintenance / Licenses --------------------
@main.route("/employees")
@login_required
@role_required("Admin", "IT", "Manager")
def employees():
    employees = Employee.query.order_by(Employee.id.asc()).all()
    return render_template("employees/list.html", employees=employees)

@main.route("/employees/new", methods=["GET", "POST"])
@login_required
@role_required("Admin", "IT")
def employee_new():
    if request.method == "POST":
        emp = Employee(
            name=request.form["name"],
            department=request.form.get("department"),
            contact=request.form.get("contact"),
        )
        db.session.add(emp)
        db.session.commit()
        flash("Employee added", "success")
        return redirect(url_for("main.employees"))
    return render_template("employees/form.html", action="Add")

@main.route("/employees/<int:emp_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("Admin", "IT")
def employee_edit(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    if request.method == "POST":
        emp.name = request.form["name"]
        emp.department = request.form.get("department")
        emp.contact = request.form.get("contact")
        db.session.commit()
        flash("Employee updated", "success")
        return redirect(url_for("main.employees"))
    return render_template("employees/form.html", action="Edit", emp=emp)

@main.route("/employees/<int:emp_id>/delete", methods=["POST"])
@login_required
@role_required("Admin", "IT")
def employee_delete(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    db.session.delete(emp)
    db.session.commit()
    flash("Employee deleted", "info")
    return redirect(url_for("main.employees"))

@main.route("/maintenance")
@login_required
@role_required("Admin", "IT", "Manager")
def maintenance_list():
    maintenances = Maintenance.query.order_by(Maintenance.date.asc()).all()
    return render_template("maintenance/list.html", maintenances=maintenances)

@main.route("/maintenance/new", methods=["GET", "POST"])
@login_required
@role_required("Admin", "IT")
def maintenance_new():
    if request.method == "POST":
        m = Maintenance(
            asset_id=request.form.get("asset_id"),
            date=datetime.strptime(request.form["date"], "%Y-%m-%d").date() if request.form.get("date") else None,
            description=request.form.get("description"),
            cost=request.form.get("cost") or 0,
            status="Pending",
        )
        db.session.add(m)
        db.session.commit()
        flash("Maintenance record added", "success")
        return redirect(url_for("main.maintenance_list"))
    assets = Asset.query.all()
    return render_template("maintenance/form.html", action="Add", assets=assets)

@main.route("/maintenance/<int:mid>/edit", methods=["GET", "POST"])
@login_required
@role_required("Admin", "IT")
def maintenance_edit(mid):
    m = Maintenance.query.get_or_404(mid)
    if request.method == "POST":
        m.asset_id = request.form.get("asset_id")
        m.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date() if request.form.get("date") else None
        m.description = request.form.get("description")
        m.cost = request.form.get("cost") or 0
        # Keep status as-is unless explicitly changed elsewhere
        db.session.commit()
        flash("Maintenance updated", "success")
        return redirect(url_for("main.maintenance_list"))
    assets = Asset.query.all()
    return render_template("maintenance/form.html", action="Edit", assets=assets, m=m)

@main.route("/maintenance/<int:mid>/approve", methods=["POST"])
@login_required
@role_required("Admin")
def maintenance_approve(mid):
    m = Maintenance.query.get_or_404(mid)
    if m.status == "Approved":
        flash("Already approved", "info")
        return redirect(url_for("main.maintenance_list"))
    m.status = "Approved"
    m.approved_by = current_user.id
    m.approved_at = datetime.utcnow()
    db.session.commit()
    flash("Maintenance approved", "success")
    return redirect(url_for("main.admin_dashboard"))

@main.route("/maintenance/<int:mid>/delete", methods=["POST"])
@login_required
@role_required("Admin", "IT")
def maintenance_delete(mid):
    m = Maintenance.query.get_or_404(mid)
    db.session.delete(m)
    db.session.commit()
    flash("Maintenance deleted", "info")
    return redirect(url_for("main.maintenance_list"))

@main.route("/licenses")
@login_required
@role_required("Admin", "IT", "Manager")
def licenses():
    licenses = SoftwareLicense.query.order_by(SoftwareLicense.id.asc()).all()
    return render_template("licenses/list.html", licenses=licenses)

@main.route("/licenses/new", methods=["GET", "POST"])
@login_required
@role_required("Admin", "IT")
def license_new():
    if request.method == "POST":
        lic = SoftwareLicense(
            software_name=request.form["software_name"],
            license_key=request.form.get("license_key"),
            expiry_date=datetime.strptime(request.form["expiry_date"], "%Y-%m-%d").date() if request.form.get("expiry_date") else None,
            assigned_to=request.form.get("assigned_to") or None,
        )
        db.session.add(lic)
        db.session.commit()
        flash("License added", "success")
        return redirect(url_for("main.licenses"))
    employees = Employee.query.all()
    return render_template("licenses/form.html", action="Add", employees=employees)

@main.route("/licenses/<int:lid>/edit", methods=["GET", "POST"])
@login_required
@role_required("Admin", "IT")
def license_edit(lid):
    lic = SoftwareLicense.query.get_or_404(lid)
    if request.method == "POST":
        lic.software_name = request.form["software_name"]
        lic.license_key = request.form.get("license_key")
        lic.expiry_date = datetime.strptime(request.form["expiry_date"], "%Y-%m-%d").date() if request.form.get("expiry_date") else None
        lic.assigned_to = request.form.get("assigned_to") or None
        db.session.commit()
        flash("License updated", "success")
        return redirect(url_for("main.licenses"))
    employees = Employee.query.all()
    return render_template("licenses/form.html", action="Edit", employees=employees, lic=lic)

@main.route("/licenses/<int:lid>/delete", methods=["POST"])
@login_required
@role_required("Admin", "IT")
def license_delete(lid):
    lic = SoftwareLicense.query.get_or_404(lid)
    db.session.delete(lic)
    db.session.commit()
    flash("License deleted", "info")
    return redirect(url_for("main.licenses"))

# -------------------- Assets CRUD --------------------
@main.route("/assets")
@login_required
@role_required("Admin", "IT", "Manager")
def assets():
    assets = Asset.query.order_by(Asset.id.asc()).all()
    return render_template("assets/list.html", assets=assets)

@main.route("/assets/new", methods=["GET", "POST"])
@login_required
@role_required("Admin", "IT")
def asset_new():
    if request.method == "POST":
        data = request.form
        asset = Asset(
            asset_id=data["asset_id"],
            asset_type=data.get("asset_type"),
            brand=data.get("brand"),
            model=data.get("model"),
            serial_no=data.get("serial_no"),
            purchase_date=datetime.strptime(data.get("purchase_date"), "%Y-%m-%d").date() if data.get("purchase_date") else None,
            warranty_expiry=datetime.strptime(data.get("warranty_expiry"), "%Y-%m-%d").date() if data.get("warranty_expiry") else None,
            status=data.get("status"),
            assigned_to=data.get("assigned_to") or None,
        )
        db.session.add(asset)
        db.session.commit()
        flash("Asset added", "success")
        return redirect(url_for("main.assets"))
    employees = Employee.query.all()
    return render_template("assets/form.html", employees=employees, action="Add")

@main.route("/assets/<int:asset_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("Admin", "IT")
def asset_edit(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if request.method == "POST":
        data = request.form
        asset.asset_type = data.get("asset_type")
        asset.brand = data.get("brand")
        asset.model = data.get("model")
        asset.serial_no = data.get("serial_no")
        asset.purchase_date = datetime.strptime(data.get("purchase_date"), "%Y-%m-%d").date() if data.get("purchase_date") else None
        asset.warranty_expiry = datetime.strptime(data.get("warranty_expiry"), "%Y-%m-%d").date() if data.get("warranty_expiry") else None
        asset.status = data.get("status")
        asset.assigned_to = data.get("assigned_to") or None
        db.session.commit()
        flash("Asset updated", "success")
        return redirect(url_for("main.assets"))
    employees = Employee.query.all()
    return render_template("assets/form.html", asset=asset, employees=employees, action="Edit")

@main.route("/assets/<int:asset_id>/delete", methods=["POST"])
@login_required
@role_required("Admin", "IT")
def asset_delete(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    db.session.delete(asset)
    db.session.commit()
    flash("Asset deleted", "info")
    return redirect(url_for("main.assets"))

# -------------------- Export Routes --------------------
@main.route("/export/assets/csv")
@login_required
@role_required("Admin", "IT", "Manager")
def export_assets_csv():
    assets = Asset.query.all()
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Asset ID', 'Type', 'Brand', 'Model', 'Serial No', 'Purchase Date', 'Warranty Expiry', 'Status', 'Assigned To'])
    
    for asset in assets:
        writer.writerow([
            asset.asset_id,
            asset.asset_type,
            asset.brand,
            asset.model,
            asset.serial_no,
            asset.purchase_date.strftime('%Y-%m-%d') if asset.purchase_date else '',
            asset.warranty_expiry.strftime('%Y-%m-%d') if asset.warranty_expiry else '',
            asset.status,
            asset.assigned_to
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=assets.csv'}
    )

@main.route("/export/employees/csv")
@login_required
@role_required("Admin", "IT", "Manager")
def export_employees_csv():
    employees = Employee.query.all()
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Name', 'Department', 'Contact'])
    
    for emp in employees:
        writer.writerow([emp.id, emp.name, emp.department, emp.contact])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=employees.csv'}
    )

@main.route("/export/maintenance/csv")
@login_required
@role_required("Admin", "IT", "Manager")
def export_maintenance_csv():
    maintenance_records = Maintenance.query.all()
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Asset ID', 'Date', 'Description', 'Cost'])
    
    for record in maintenance_records:
        writer.writerow([
            record.id,
            record.asset_id,
            record.date.strftime('%Y-%m-%d') if record.date else '',
            record.description,
            record.cost
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=maintenance.csv'}
    )

@main.route("/export/licenses/csv")
@login_required
@role_required("Admin", "IT", "Manager")
def export_licenses_csv():
    licenses = SoftwareLicense.query.all()
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Software Name', 'License Key', 'Expiry Date', 'Assigned To'])
    
    for lic in licenses:
        writer.writerow([
            lic.id,
            lic.software_name,
            lic.license_key,
            lic.expiry_date.strftime('%Y-%m-%d') if lic.expiry_date else '',
            lic.assigned_to
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=licenses.csv'}
    )

# Excel Export Routes
@main.route("/export/assets/excel")
@login_required
@role_required("Admin", "IT", "Manager")
def export_assets_excel():
    if not PANDAS_AVAILABLE:
        flash("Pandas not available. Please install pandas to enable Excel export.", "warning")
        return redirect(url_for("main.assets"))
    
    assets = Asset.query.all()
    data = []
    
    for asset in assets:
        data.append({
            'Asset ID': asset.asset_id,
            'Type': asset.asset_type,
            'Brand': asset.brand,
            'Model': asset.model,
            'Serial No': asset.serial_no,
            'Purchase Date': asset.purchase_date.strftime('%Y-%m-%d') if asset.purchase_date else '',
            'Warranty Expiry': asset.warranty_expiry.strftime('%Y-%m-%d') if asset.warranty_expiry else '',
            'Status': asset.status,
            'Assigned To': asset.assigned_to
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=assets.xlsx'}
    )

@main.route("/export/employees/excel")
@login_required
@role_required("Admin", "IT", "Manager")
def export_employees_excel():
    if not PANDAS_AVAILABLE:
        flash("Pandas not available. Please install pandas to enable Excel export.", "warning")
        return redirect(url_for("main.employees"))
    
    employees = Employee.query.all()
    data = []
    
    for emp in employees:
        data.append({
            'ID': emp.id,
            'Name': emp.name,
            'Department': emp.department,
            'Contact': emp.contact
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=employees.xlsx'}
    )

@main.route("/export/maintenance/excel")
@login_required
@role_required("Admin", "IT", "Manager")
def export_maintenance_excel():
    if not PANDAS_AVAILABLE:
        flash("Pandas not available. Please install pandas to enable Excel export.", "warning")
        return redirect(url_for("main.maintenance_list"))
    
    maintenance_records = Maintenance.query.all()
    data = []
    
    for record in maintenance_records:
        data.append({
            'ID': record.id,
            'Asset ID': record.asset_id,
            'Date': record.date.strftime('%Y-%m-%d') if record.date else '',
            'Description': record.description,
            'Cost': record.cost
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=maintenance.xlsx'}
    )

@main.route("/export/licenses/excel")
@login_required
@role_required("Admin", "IT", "Manager")
def export_licenses_excel():
    if not PANDAS_AVAILABLE:
        flash("Pandas not available. Please install pandas to enable Excel export.", "warning")
        return redirect(url_for("main.licenses"))
    
    licenses = SoftwareLicense.query.all()
    data = []
    
    for lic in licenses:
        data.append({
            'ID': lic.id,
            'Software Name': lic.software_name,
            'License Key': lic.license_key,
            'Expiry Date': lic.expiry_date.strftime('%Y-%m-%d') if lic.expiry_date else '',
            'Assigned To': lic.assigned_to
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=licenses.xlsx'}
    )

# -------------------- Email Notification Functions --------------------
def send_license_expiry_notifications(
    cc_admin_it: bool = False,
    days_override: int | None = None,
    extra_cc: list[str] | None = None,
    extra_to: list[str] | None = None,
    assignees_only: bool = True,
) -> dict:
    """Send email notifications for licenses expiring soon.

    - Sends to license assignees (Employee.contact as email).
    - If cc_admin_it=True, Admin/IT emails are CC'd on each message.
    - days_override: override window (days) to consider.
    - extra_cc=["cudjoetairo@gmail.com"]: additional emails to CC on each message.
    - assignees_only: if False and no assignees found, fallback to Admin/IT broadcast.

    Returns a summary dict with counts and recipient lists.
    """
    if not MAIL_AVAILABLE:
        print("Flask-Mail not available. Skipping license expiry notifications.")
        return
        
    from app import create_app
    app = create_app()
    
    with app.app_context():
        summary = {
            'type': 'license',
            'window_days': days_override or app.config['LICENSE_EXPIRY_DAYS'],
            'assignee_emails_sent': 0,
            'fallback_admin_it_emails_sent': 0,
            'skipped_no_email': 0,
            'assignee_recipients': [],
            'admin_it_recipients': [],
            'extra_to_emails_sent': 0,
            'extra_to_recipients': [],
        }
        # Get licenses expiring within the configured days
        window_days = days_override or app.config['LICENSE_EXPIRY_DAYS']
        expiry_threshold = datetime.now() + timedelta(days=window_days)
        expiring_licenses = SoftwareLicense.query.filter(
            SoftwareLicense.expiry_date <= expiry_threshold,
            SoftwareLicense.expiry_date >= datetime.now()
        ).all()
        
        if not expiring_licenses:
            return summary
        
        # Group expiring licenses by assignee (Employee.id)
        licenses_by_emp = {}
        for lic in expiring_licenses:
            if lic.assigned_to:
                licenses_by_emp.setdefault(lic.assigned_to, []).append(lic)

        # Prepare sender from first Admin/IT email or configured default
        admin_it_users = User.query.filter(User.role.in_(['Admin', 'IT'])).all()
        admin_it_emails = [u.email for u in admin_it_users if u.email]
        computed_sender = (admin_it_emails[0] if admin_it_emails else app.config.get('MAIL_DEFAULT_SENDER'))

        # If no assignees to notify, optionally send to extra_to and/or fall back to Admin/IT
        if not licenses_by_emp:
            # Build CC list for Admin/IT if requested
            cc_emails = []
            if cc_admin_it:
                cc_emails = admin_it_emails
            if extra_cc:
                cc_emails.extend([e for e in extra_cc if e])

            # Send direct To emails if provided (even when there are no assignees)
            if extra_to:
                for email in [e.strip() for e in extra_to if e and '@' in e]:
                    msg = Message(
                        subject=f'License Expiry Notifications - {len(expiring_licenses)} licenses expiring soon',
                        recipients=[email],
                        sender=computed_sender,
                        cc=cc_emails if cc_emails else None,
                        html=render_template(
                            'emails/license_expiry.html',
                            licenses=expiring_licenses,
                            user={'name': email},
                            days=window_days,
                            now=datetime.now
                        )
                    )
                    try:
                        mail.send(msg)
                        summary['extra_to_emails_sent'] += 1
                        summary['extra_to_recipients'].append(email)
                    except Exception as e:
                        print(f"Failed to send email to {email}: {e}")

            if not assignees_only:
                for user in admin_it_users:
                    if user.email:
                        msg = Message(
                            subject=f'License Expiry Notifications - {len(expiring_licenses)} licenses expiring soon',
                            recipients=[user.email],
                            sender=computed_sender,
                            html=render_template(
                                'emails/license_expiry.html',
                                licenses=expiring_licenses,
                                user=user,
                                days=window_days,
                                now=datetime.now
                            )
                        )
                        try:
                            mail.send(msg)
                            summary['fallback_admin_it_emails_sent'] += 1
                            summary['admin_it_recipients'].append(user.email)
                        except Exception as e:
                            print(f"Failed to send email to {user.email}: {e}")
            return summary

        # Build CC list for Admin/IT if requested
        cc_emails = []
        if cc_admin_it:
            cc_emails = admin_it_emails
        if extra_cc:
            cc_emails.extend([e for e in extra_cc if e])

        # Fetch employees for email/addressing
        emp_ids = list(licenses_by_emp.keys())
        employees = Employee.query.filter(Employee.id.in_(emp_ids)).all()
        emp_index = {e.id: e for e in employees}

        # Send individualized emails to each assignee
        for emp_id, lic_list in licenses_by_emp.items():
            emp = emp_index.get(emp_id)
            if not emp:
                continue
            # Use Employee.contact as email if it looks valid
            to_email = (emp.contact or '').strip() if emp.contact and '@' in emp.contact else None
            if not to_email:
                summary['skipped_no_email'] += 1
                continue

            # Minimal user object for template compatibility
            user_ctx = {'name': emp.name}
            msg = Message(
                subject=f'License Expiry Notice - {len(lic_list)} license(s) assigned to you expiring soon',
                recipients=[to_email],
                sender=computed_sender,
                cc=cc_emails if cc_emails else None,
                html=render_template(
                    'emails/license_expiry.html',
                    licenses=lic_list,
                    user=user_ctx,
                    days=window_days,
                    now=datetime.now
                )
            )
            try:
                mail.send(msg)
                summary['assignee_emails_sent'] += 1
                summary['assignee_recipients'].append(to_email)
            except Exception as e:
                print(f"Failed to send email to {to_email}: {e}")
        return summary

def send_warranty_expiry_notifications(
    cc_admin_it: bool = False,
    days_override: int | None = None,
    extra_cc: list[str] | None = None,
    extra_to: list[str] | None = None,
    assignees_only: bool = True,
) -> dict:
    """Send email notifications for warranties expiring soon.

    - Sends to asset assignees (Employee.contact as email).
    - If cc_admin_it=True, Admin/IT emails are CC'd on each message.
    - days_override: override window (days) to consider.
    - extra_cc: additional emails to CC on each message.
    - assignees_only: if False and no assignees found, fallback to Admin/IT broadcast.

    Returns a summary dict with counts and recipient lists.
    """
    if not MAIL_AVAILABLE:
        print("Flask-Mail not available. Skipping warranty expiry notifications.")
        return
        
    from app import create_app
    app = create_app()
    
    with app.app_context():
        summary = {
            'type': 'warranty',
            'window_days': days_override or app.config['WARRANTY_EXPIRY_DAYS'],
            'assignee_emails_sent': 0,
            'fallback_admin_it_emails_sent': 0,
            'skipped_no_email': 0,
            'assignee_recipients': [],
            'admin_it_recipients': [],
            'extra_to_emails_sent': 0,
            'extra_to_recipients': [],
        }
        # Get assets with warranties expiring within the configured days
        window_days = days_override or app.config['WARRANTY_EXPIRY_DAYS']
        expiry_threshold = datetime.now() + timedelta(days=window_days)
        expiring_warranties = Asset.query.filter(
            Asset.warranty_expiry <= expiry_threshold,
            Asset.warranty_expiry >= datetime.now()
        ).all()
        
        if not expiring_warranties:
            return summary
        
        # Group expiring assets by assignee (Employee.id)
        assets_by_emp = {}
        for asset in expiring_warranties:
            if asset.assigned_to:
                assets_by_emp.setdefault(asset.assigned_to, []).append(asset)

        # Prepare sender from first Admin/IT email or configured default
        admin_it_users = User.query.filter(User.role.in_(['Admin', 'IT'])).all()
        admin_it_emails = [u.email for u in admin_it_users if u.email]
        computed_sender = (admin_it_emails[0] if admin_it_emails else app.config.get('MAIL_DEFAULT_SENDER'))

        # If no assignees to notify, optionally fall back to Admin/IT
        if not assets_by_emp:
            # Build CC list for Admin/IT if requested
            cc_emails = []
            if cc_admin_it:
                cc_emails = admin_it_emails
            if extra_cc:
                cc_emails.extend([e for e in extra_cc if e])

            # Send direct To emails if provided (even when there are no assignees)
            if extra_to:
                for email in [e.strip() for e in extra_to if e and '@' in e]:
                    msg = Message(
                        subject=f'Warranty Expiry Notifications - {len(expiring_warranties)} warranties expiring soon',
                        recipients=[email],
                        sender=computed_sender,
                        cc=cc_emails if cc_emails else None,
                        html=render_template(
                            'emails/warranty_expiry.html',
                            assets=expiring_warranties,
                            user={'name': email},
                            days=window_days,
                            now=datetime.now
                        )
                    )
                    try:
                        mail.send(msg)
                        summary['extra_to_emails_sent'] += 1
                        summary['extra_to_recipients'].append(email)
                    except Exception as e:
                        print(f"Failed to send email to {email}: {e}")

            if not assignees_only:
                for user in admin_it_users:
                    if user.email:
                        msg = Message(
                            subject=f'Warranty Expiry Notifications - {len(expiring_warranties)} warranties expiring soon',
                            recipients=[user.email],
                            sender=computed_sender,
                            html=render_template(
                                'emails/warranty_expiry.html',
                                assets=expiring_warranties,
                                user=user,
                                days=window_days,
                                now=datetime.now
                            )
                        )
                        try:
                            mail.send(msg)
                            summary['fallback_admin_it_emails_sent'] += 1
                            summary['admin_it_recipients'].append(user.email)
                        except Exception as e:
                            print(f"Failed to send email to {user.email}: {e}")
            return summary

        # Build CC list for Admin/IT if requested
        cc_emails = []
        if cc_admin_it:
            cc_emails = admin_it_emails
        if extra_cc:
            cc_emails.extend([e for e in extra_cc if e])

        # Fetch employees for email/addressing
        emp_ids = list(assets_by_emp.keys())
        employees = Employee.query.filter(Employee.id.in_(emp_ids)).all()
        emp_index = {e.id: e for e in employees}

        # Send individualized emails to each assignee
        for emp_id, asset_list in assets_by_emp.items():
            emp = emp_index.get(emp_id)
            if not emp:
                continue
            to_email = (emp.contact or '').strip() if emp.contact and '@' in emp.contact else None
            if not to_email:
                summary['skipped_no_email'] += 1
                continue

            user_ctx = {'name': emp.name}
            msg = Message(
                subject=f'Warranty Expiry Notice - {len(asset_list)} asset(s) assigned to you expiring soon',
                recipients=[to_email],
                sender=computed_sender,
                cc=cc_emails if cc_emails else None,
                html=render_template(
                    'emails/warranty_expiry.html',
                    assets=asset_list,
                    user=user_ctx,
                    days=window_days,
                    now=datetime.now
                )
            )
            try:
                mail.send(msg)
                summary['assignee_emails_sent'] += 1
                summary['assignee_recipients'].append(to_email)
            except Exception as e:
                print(f"Failed to send email to {to_email}: {e}")
        return summary

# -------------------- Notification Routes --------------------
@main.route("/notifications/test-license")
@login_required
@role_required("Admin", "IT", "Manager")
def test_license_notifications():
    """Test route to send license expiry notifications."""
    if not MAIL_AVAILABLE:
        flash("Flask-Mail not available. Please install Flask-Mail to enable email notifications.", "warning")
        return redirect(url_for("main.it_dashboard"))
    
    # Optional CC to Admin/IT via query param: /notifications/test-license?cc=1
    cc = str(request.args.get('cc', '0')).lower() in ("1", "true", "yes", "on")
    send_license_expiry_notifications(cc_admin_it=cc)
    flash("License expiry notifications sent successfully!", "success")
    return redirect(url_for("main.it_dashboard"))

@main.route("/notifications/test-warranty")
@login_required
@role_required("Admin", "IT", "Manager")
def test_warranty_notifications():
    """Test route to send warranty expiry notifications."""
    if not MAIL_AVAILABLE:
        flash("Flask-Mail not available. Please install Flask-Mail to enable email notifications.", "warning")
        return redirect(url_for("main.it_dashboard"))
    
    # Optional CC to Admin/IT via query param: /notifications/test-warranty?cc=1
    cc = str(request.args.get('cc', '0')).lower() in ("1", "true", "yes", "on")
    send_warranty_expiry_notifications(cc_admin_it=cc)
    flash("Warranty expiry notifications sent successfully!", "success")
    return redirect(url_for("main.it_dashboard"))

# -------------------- Notifications Send Page --------------------
@main.route("/notifications/send", methods=["GET", "POST"])
@login_required
@role_required("Admin", "IT", "Manager")
def notifications_send():
    """Form to send license/warranty notifications with options. Shows a result summary after sending."""
    if request.method == "POST":
        notif_type = request.form.get('type', 'warranty')
        window_days = request.form.get('days')
        cc_admin_it = bool(request.form.get('cc_admin_it'))
        assignees_only = bool(request.form.get('assignees_only'))
        extra_raw = request.form.get('additional_recipients', '')
        extra_cc = [e.strip() for e in extra_raw.split(',') if e.strip()]
        extra_to_raw = request.form.get('additional_to_recipients', '')
        extra_to = [e.strip() for e in extra_to_raw.split(',') if e.strip()]

        days_override = int(window_days) if window_days and window_days.isdigit() else None

        summary = {}
        if notif_type == 'license':
            summary = send_license_expiry_notifications(
                cc_admin_it=cc_admin_it,
                days_override=days_override,
                extra_cc=extra_cc,
                extra_to=extra_to,
                assignees_only=assignees_only,
            )
        else:
            summary = send_warranty_expiry_notifications(
                cc_admin_it=cc_admin_it,
                days_override=days_override,
                extra_cc=extra_cc,
                extra_to=extra_to,
                assignees_only=assignees_only,
            )

        return render_template('notifications/result.html', summary=summary)

    # Defaults for GET
    license_days_default = current_app.config.get('LICENSE_EXPIRY_DAYS', 30)
    warranty_days_default = current_app.config.get('WARRANTY_EXPIRY_DAYS', 30)
    return render_template('notifications/send.html',
                           license_days_default=license_days_default,
                           warranty_days_default=warranty_days_default)

# -------------------- Reports & Notifications Center --------------------
@main.route("/reports")
@login_required
@role_required("Admin", "IT", "Manager")
def reports():
    """Reports overview with quick exports and KPIs."""
    total_assets = Asset.query.count()
    total_employees = Employee.query.count()
    total_licenses = SoftwareLicense.query.count()
    maintenance_count = Maintenance.query.count()
    return render_template("reports/overview.html", **locals())

@main.route("/notifications")
@login_required
@role_required("Admin", "IT", "Manager")
def notifications_center():
    """Notifications center showing upcoming expirations."""
    from datetime import date, timedelta
    today = date.today()
    licenses_expiring = SoftwareLicense.query.filter(
        SoftwareLicense.expiry_date >= today,
        SoftwareLicense.expiry_date <= today + timedelta(days=30)
    ).order_by(SoftwareLicense.expiry_date).limit(20).all()
    warranties_expiring = Asset.query.filter(
        Asset.warranty_expiry >= today,
        Asset.warranty_expiry <= today + timedelta(days=30)
    ).order_by(Asset.warranty_expiry).limit(20).all()
    return render_template("notifications/center.html", **locals())
