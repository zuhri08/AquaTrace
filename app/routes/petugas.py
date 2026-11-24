from flask import abort, Blueprint, flash, g, redirect, render_template, request, session, url_for

from app import db
from app.models import Sample, WaterSource
from app.routes.auth import role_required
from app.services.antrean import build_sample_queue, process_next_sample
from app.services.diagnosis import (
    MEASUREMENT_FIELDS,
    MEASUREMENT_ORDER,
    build_diagnosis_trail,
    save_result,
    undo_latest_result,
)
from app.services.jaringan import trace_downstream
from app.services.riwayat import (
    build_source_history,
    correct_history_entry,
    delete_history_entry,
)
from app.services.undo import build_undo_stack

petugas_bp = Blueprint("petugas", __name__, url_prefix="/petugas")


@petugas_bp.get("/antrean")
@role_required("petugas_lab", "admin")
def antrean():
    queue = build_sample_queue()
    lanes = queue.display()
    return render_template(
        "petugas/antrean.html",
        priority_samples=lanes["priority"],
        regular_samples=lanes["regular"],
        total=queue.size(),
    )


@petugas_bp.post("/antrean/proses-next")
@role_required("petugas_lab", "admin")
def proses_next():
    sample = process_next_sample()
    if sample is None:
        flash("Tidak ada sampel yang menunggu.", "info")
        return redirect(url_for("petugas.antrean"))
    flash(f"Sampel #{sample.id} diambil untuk diproses.", "success")
    return redirect(url_for("petugas.diagnosis", sample_id=sample.id))


@petugas_bp.route("/diagnosis/<int:sample_id>", methods=["GET", "POST"])
@role_required("petugas_lab", "admin")
def diagnosis(sample_id):
    sample = Sample.query.filter_by(id=sample_id, status="diproses").first_or_404()
    key = f"diagnosis:{sample.id}"
    measurements = session.get(key, {})
    trail = build_diagnosis_trail(measurements)
    step = next(
        (field for field in MEASUREMENT_ORDER if field not in measurements), "review"
    )
    if request.method == "POST":
        action = request.form.get("action", "next")
        if action == "back":
            last = trail.pop() if not trail.is_empty() else None
            if last:
                measurements.pop(last["field"], None)
                session[key] = measurements
            return redirect(url_for("petugas.diagnosis", sample_id=sample.id))
        if action == "save":
            if step != "review":
                flash("Lengkapi semua pengukuran sebelum menyimpan hasil.", "error")
                return redirect(url_for("petugas.diagnosis", sample_id=sample.id))
            try:
                result = save_result(sample.id, g.user.id, measurements)
            except ValueError as error:
                flash(str(error), "error")
                return redirect(url_for("petugas.diagnosis", sample_id=sample.id))
            session.pop(key, None)
            flash(f"Hasil sampel #{sample.id} tersimpan: {result.vonis}.", "success")
            return redirect(url_for("petugas.riwayat_entri"))

        field = request.form.get("field")
        if field != step or field not in MEASUREMENT_FIELDS:
            flash("Langkah diagnosis tidak sesuai.", "error")
            return redirect(url_for("petugas.diagnosis", sample_id=sample.id))
        try:
            value = float(request.form.get("value", ""))
            if not (MEASUREMENT_FIELDS[field]["minimum"] <= value <= MEASUREMENT_FIELDS[field]["maximum"]):
                raise ValueError
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError
        except (TypeError, ValueError):
            flash(
                f"Nilai {MEASUREMENT_FIELDS[field]['label']} harus berupa angka dalam rentang fisik.",
                "error",
            )
            return redirect(url_for("petugas.diagnosis", sample_id=sample.id))
        measurements[field] = value
        session[key] = measurements
        return redirect(url_for("petugas.diagnosis", sample_id=sample.id))

    verdict = None
    trace = []
    if step == "review":
        from app.services.diagnosis import evaluate_measurements

        verdict, trace = evaluate_measurements(measurements)
    return render_template(
        "petugas/diagnosis.html",
        sample=sample,
        step=step,
        field=MEASUREMENT_FIELDS.get(step),
        field_name=step,
        measurements=measurements,
        trail=trail.to_list(),
        verdict=verdict,
        trace=trace,
        thresholds_example=True,
    )


@petugas_bp.get("/riwayat-entri")
@role_required("petugas_lab", "admin")
def riwayat_entri():
    stack = build_undo_stack(g.user.id)
    return render_template("petugas/undo.html", actions=stack.to_list())


@petugas_bp.post("/riwayat-entri/undo")
@role_required("petugas_lab", "admin")
def undo_entri():
    try:
        sample = undo_latest_result(g.user.id)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("petugas.riwayat_entri"))
    if sample is None:
        flash("Belum ada entri yang dapat diurungkan.", "info")
        return redirect(url_for("petugas.riwayat_entri"))
    flash(f"Hasil sampel #{sample.id} diurungkan; sampel kembali menunggu.", "success")
    return redirect(url_for("petugas.riwayat_entri"))


@petugas_bp.get("/sumber/<int:source_id>/riwayat")
@role_required("petugas_lab", "admin")
def riwayat_sumber(source_id):
    history = build_source_history(source_id)
    if db.session.get(WaterSource, source_id) is None:
        abort(404)
    return render_template(
        "petugas/riwayat.html",
        source_id=source_id,
        entries=history.traverse(),
    )


@petugas_bp.post("/sumber/<int:source_id>/riwayat/<int:result_id>/hapus")
@role_required("petugas_lab", "admin")
def hapus_riwayat(source_id, result_id):
    result = delete_history_entry(source_id, result_id)
    if result is None:
        abort(404)
    flash(f"Entri #{result.id} dihapus; sampel kembali menunggu.", "success")
    return redirect(url_for("petugas.riwayat_sumber", source_id=source_id))


@petugas_bp.post("/sumber/<int:source_id>/riwayat/<int:result_id>/koreksi")
@role_required("petugas_lab", "admin")
def koreksi_riwayat(source_id, result_id):
    measurements = {
        "ph": request.form.get("ph"),
        "kekeruhan_ntu": request.form.get("kekeruhan_ntu"),
        "tds_mgl": request.form.get("tds_mgl"),
    }
    try:
        result = correct_history_entry(source_id, result_id, measurements)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("petugas.riwayat_sumber", source_id=source_id))
    if result is None:
        abort(404)
    flash(f"Entri #{result.id} berhasil dikoreksi: {result.vonis}.", "success")
    return redirect(url_for("petugas.riwayat_sumber", source_id=source_id))


@petugas_bp.route("/lacak-dampak", methods=["GET", "POST"])
@role_required("petugas_lab", "admin")
def lacak_dampak():
    from app.models import WaterSource
    from app.services.jaringan import network_snapshot

    sources, edges = network_snapshot()
    impacted = []
    selected_source_id = None
    if request.method == "POST":
        try:
            selected_source_id = int(request.form.get("source_id", ""))
            impacted = trace_downstream(selected_source_id)
        except (ValueError, LookupError) as error:
            flash(str(error), "error")
    return render_template(
        "petugas/lacak_dampak.html",
        sources=sources,
        edges=edges,
        impacted=impacted,
        selected_source_id=selected_source_id,
    )
