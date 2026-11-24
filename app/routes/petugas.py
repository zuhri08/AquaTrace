import json

from flask import Blueprint, flash, g, redirect, render_template, url_for

from app import db
from app.models import EntryAction, Sample
from app.routes.auth import role_required
from app.services.antrean import build_sample_queue, process_next_sample
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


@petugas_bp.get("/diagnosis/<int:sample_id>")
@role_required("petugas_lab", "admin")
def diagnosis(sample_id):
    sample = Sample.query.filter_by(id=sample_id, status="diproses").first_or_404()
    return render_template("petugas/diagnosis.html", sample=sample)


@petugas_bp.get("/riwayat-entri")
@role_required("petugas_lab", "admin")
def riwayat_entri():
    stack = build_undo_stack(g.user.id)
    return render_template("petugas/undo.html", actions=stack.to_list())


@petugas_bp.post("/riwayat-entri/undo")
@role_required("petugas_lab", "admin")
def undo_entri():
    action = (
        EntryAction.query.filter_by(user_id=g.user.id)
        .order_by(EntryAction.created_at.desc(), EntryAction.id.desc())
        .first()
    )
    if action is None:
        flash("Belum ada entri yang dapat diurungkan.", "info")
        return redirect(url_for("petugas.riwayat_entri"))
    payload = json.loads(action.payload_json)
    if action.aksi != "simpan_hasil":
        flash("Jenis aksi ini belum dapat diurungkan.", "error")
        return redirect(url_for("petugas.riwayat_entri"))
    sample = db.session.get(Sample, payload["sample_id"])
    if sample is None or sample.status != "selesai":
        flash("Hasil tidak dapat diurungkan karena status sampel sudah berubah.", "error")
        return redirect(url_for("petugas.riwayat_entri"))
    if sample.test_results:
        db.session.delete(sample.test_results[-1])
    sample.status = "menunggu"
    db.session.delete(action)
    db.session.commit()
    flash(f"Hasil sampel #{sample.id} diurungkan; sampel kembali menunggu.", "success")
    return redirect(url_for("petugas.riwayat_entri"))
