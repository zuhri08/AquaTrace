from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app import db
from app.models import Region, Sample, WaterSource
from app.routes.auth import role_required
from app.services.antrean import queue_position, submit_sample

warga_bp = Blueprint("warga", __name__, url_prefix="/warga")


@warga_bp.route("/sumber/baru", methods=["GET", "POST"])
@role_required("warga")
def sumber_baru():
    if request.method == "POST":
        try:
            region_id = int(request.form.get("region_id", ""))
            lat = float(request.form.get("lat", ""))
            lng = float(request.form.get("lng", ""))
        except ValueError:
            flash("Wilayah dan koordinat harus berupa nilai yang valid.", "error")
            return redirect(url_for("warga.sumber_baru"))
        nama = request.form.get("nama", "").strip()
        tipe = request.form.get("tipe", "")
        region = db.session.get(Region, region_id)
        if not nama or len(nama) > 160 or region is None:
            flash("Nama sumber atau wilayah tidak valid.", "error")
            return redirect(url_for("warga.sumber_baru"))
        if tipe not in {"sumur", "sungai", "pdam", "mata_air"}:
            flash("Jenis sumber tidak valid.", "error")
            return redirect(url_for("warga.sumber_baru"))
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            flash("Koordinat berada di luar rentang yang valid.", "error")
            return redirect(url_for("warga.sumber_baru"))
        source = WaterSource(
            nama=nama,
            tipe=tipe,
            region_id=region.id,
            lat=lat,
            lng=lng,
            dibuat_oleh=g.user.id,
        )
        db.session.add(source)
        db.session.commit()
        flash("Sumber air berhasil dilaporkan.", "success")
        return redirect(url_for("warga.dashboard"))

    return render_template(
        "warga/sumber_baru.html", regions=Region.query.order_by(Region.nama).all()
    )


@warga_bp.get("/dashboard")
@role_required("warga")
def dashboard():
    sources = WaterSource.query.filter_by(dibuat_oleh=g.user.id).order_by(WaterSource.id).all()
    samples = (
        Sample.query.filter_by(diajukan_oleh=g.user.id)
        .order_by(Sample.created_at.desc())
        .all()
    )
    return render_template("warga/dashboard.html", sources=sources, samples=samples)


@warga_bp.route("/sampel/baru", methods=["GET", "POST"])
@role_required("warga")
def sampel_baru():
    sources = WaterSource.query.filter_by(dibuat_oleh=g.user.id).order_by(WaterSource.id).all()
    if request.method == "POST":
        try:
            source_id = int(request.form.get("source_id", ""))
        except ValueError:
            flash("Pilih sumber air yang valid.", "error")
            return redirect(url_for("warga.sampel_baru"))
        source = WaterSource.query.filter_by(
            id=source_id, dibuat_oleh=g.user.id
        ).first()
        if source is None:
            flash("Sumber air tidak ditemukan pada akun Anda.", "error")
            return redirect(url_for("warga.sampel_baru"))
        sample = submit_sample(
            source.id,
            g.user.id,
            priority=request.form.get("prioritas") == "yes",
        )
        flash(f"Sampel #{sample.id} masuk antrean.", "success")
        return redirect(url_for("warga.sampel_detail", sample_id=sample.id))
    return render_template("warga/sampel_baru.html", sources=sources)


@warga_bp.get("/sampel/<int:sample_id>")
@role_required("warga")
def sampel_detail(sample_id):
    sample = Sample.query.filter_by(
        id=sample_id, diajukan_oleh=g.user.id
    ).first_or_404()
    return render_template(
        "warga/sampel_detail.html",
        sample=sample,
        position=queue_position(sample.id),
    )
