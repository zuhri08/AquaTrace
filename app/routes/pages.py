from flask import Blueprint, render_template

from app.routes.auth import role_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def landing():
    return render_template("landing.html")


@pages_bp.get("/petugas/dashboard")
@role_required("petugas_lab", "admin")
def petugas_dashboard():
    return render_template("dashboard.html", dashboard_role="Petugas laboratorium")


@pages_bp.get("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    return render_template("dashboard.html", dashboard_role="Administrator")
