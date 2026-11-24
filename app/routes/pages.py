from flask import Blueprint, render_template

from app.routes.auth import role_required
from app.services.jaringan import nearest_clean_source
from app.services.wilayah import region_dashboard_data

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
    region_tree, contaminated_count = region_dashboard_data()
    return render_template(
        "admin/dashboard.html",
        region_tree=region_tree,
        contaminated_count=contaminated_count,
    )


@pages_bp.route("/warga/terdekat", methods=["GET", "POST"])
@role_required("warga")
def warga_terdekat():
    from flask import flash, redirect, request, url_for

    from app.models import WaterSource

    sources = WaterSource.query.order_by(WaterSource.nama).all()
    result = None
    if request.method == "POST":
        try:
            source_id = int(request.form.get("source_id", ""))
            result = nearest_clean_source(source_id)
        except (ValueError, LookupError) as error:
            flash(str(error), "error")
        return render_template("warga/terdekat.html", sources=sources, result=result)
    return render_template("warga/terdekat.html", sources=sources, result=result)
