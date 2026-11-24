from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.models import RiverEdge
from app.routes.auth import role_required
from app.services.jaringan import add_river_edge, network_snapshot, remove_river_edge

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/jaringan", methods=["GET", "POST"])
@role_required("admin")
def jaringan():
    if request.method == "POST":
        try:
            source_id = int(request.form.get("dari_source_id", ""))
            target_id = int(request.form.get("ke_source_id", ""))
            distance = request.form.get("jarak_km", "")
            edge = add_river_edge(source_id, target_id, distance)
        except (ValueError, TypeError) as error:
            flash(str(error), "error")
        else:
            flash(f"Edge #{edge.id} berhasil ditambahkan.", "success")
        return redirect(url_for("admin.jaringan"))
    sources, edges = network_snapshot()
    return render_template("admin/jaringan.html", sources=sources, edges=edges)


@admin_bp.post("/jaringan/<int:edge_id>/hapus")
@role_required("admin")
def hapus_edge(edge_id):
    edge = remove_river_edge(edge_id)
    if edge is None:
        abort(404)
    flash(f"Edge #{edge.id} berhasil dihapus.", "success")
    return redirect(url_for("admin.jaringan"))
