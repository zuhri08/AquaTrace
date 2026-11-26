from flask import Blueprint, render_template

from app.models import IotDevice, TestResult, WaterSource
from app.routes.auth import role_required
from app.services.jaringan import nearest_clean_source
from app.services.wilayah import region_dashboard_data

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def landing():
    return render_template("landing.html")


@pages_bp.get("/publik")
def publik():
    sources = WaterSource.query.order_by(WaterSource.nama).all()
    latest_results = {}
    for result in TestResult.query.order_by(
        TestResult.created_at.desc(), TestResult.id.desc()
    ).all():
        latest_results.setdefault(result.source_id, result)
    measured = len(latest_results)
    classified = sum(result.vonis is not None for result in latest_results.values())
    clean = sum(result.vonis == "BERSIH" for result in latest_results.values())
    devices = IotDevice.query.order_by(IotDevice.kode).all()
    index = round(clean * 100 / classified, 1) if classified else None
    return render_template(
        "publik/index.html",
        measured_count=measured,
        classified_count=classified,
        clean_count=clean,
        clean_index=index,
        source_count=len(sources),
        sources=sources,
        latest_results=latest_results,
        device_ids=[device.id for device in devices],
    )


@pages_bp.get("/styleguide")
@role_required("admin")
def styleguide():
    source = WaterSource.query.order_by(WaterSource.id).first()
    device = IotDevice.query.order_by(IotDevice.id).first()
    return render_template(
        "styleguide.html",
        source_id=source.id if source else None,
        device_id=device.id if device else None,
    )


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
    selected_source_id = None
    if request.method == "POST":
        try:
            selected_source_id = int(request.form.get("source_id", ""))
            result = nearest_clean_source(selected_source_id)
        except (ValueError, LookupError) as error:
            flash(str(error), "error")
        return render_template(
            "warga/terdekat.html",
            sources=sources,
            result=result,
            selected_source_id=selected_source_id,
        )
    return render_template(
        "warga/terdekat.html", sources=sources, result=result, selected_source_id=None
    )
