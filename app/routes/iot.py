from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app import db, csrf
from app.models import IotDevice, WaterSource
from app.routes.auth import role_required
from app.services.telemetri import (
    IngestError,
    accept_reading,
    build_reading_queue,
    delete_device,
    device_is_online,
    latest_readings,
    process_reading_queue,
    register_device,
    sensor_series,
)

iot_bp = Blueprint("iot", __name__)


@iot_bp.post("/api/iot/ingest")
@csrf.exempt
def ingest():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Body harus berupa JSON yang valid.", "fields": {}}), 422
    try:
        accepted = accept_reading(
            payload.get("kode"),
            request.headers.get("X-API-Key"),
            payload,
        )
    except IngestError as error:
        response = jsonify({"error": str(error), "fields": error.fields})
        if error.status_code == 429:
            response.headers["Retry-After"] = "2"
        return response, error.status_code
    if current_app.config["IOT_AUTO_PROSES"]:
        process_reading_queue()
    return (
        jsonify(
            {
                "status": "antri",
                "reading_id": accepted["reading_id"],
                "posisi_antrean": accepted["posisi_antrean"],
            }
        ),
        202,
    )


@iot_bp.get("/petugas/telemetri")
@role_required("petugas_lab", "admin")
def telemetry():
    queue = build_reading_queue()
    devices = IotDevice.query.order_by(IotDevice.kode).all()
    return render_template(
        "petugas/telemetri.html",
        devices=devices,
        readings=latest_readings(),
        queue=queue.to_list(),
        online=device_is_online,
        series=sensor_series,
    )


@iot_bp.post("/petugas/telemetri/proses")
@role_required("petugas_lab", "admin")
def process_telemetry():
    processed = process_reading_queue()
    flash(f"{len(processed)} bacaan telemetri diproses FIFO.", "success")
    return redirect(url_for("iot.telemetry"))


@iot_bp.get("/publik/telemetri")
def public_telemetry():
    devices = IotDevice.query.order_by(IotDevice.kode).all()
    return render_template(
        "publik/telemetri.html",
        devices=devices,
        readings=latest_readings(20),
        online=device_is_online,
    )


@iot_bp.route("/admin/telemetri/perangkat", methods=["GET", "POST"])
@role_required("admin")
def devices():
    if request.method == "POST":
        try:
            source_id = int(request.form.get("source_id", ""))
            device, api_key = register_device(
                source_id,
                request.form.get("kode", ""),
                request.form.get("nama", ""),
            )
        except (ValueError, TypeError) as error:
            flash(str(error), "error")
        else:
            flash(f"Perangkat {device.kode} dibuat. Simpan API key berikut sekarang.", "success")
            return (
                render_template(
                    "admin/perangkat.html",
                    devices=IotDevice.query.order_by(IotDevice.kode).all(),
                    sources=WaterSource.query.order_by(WaterSource.nama).all(),
                    online=device_is_online,
                    one_time_key=api_key,
                ),
                201,
            )
        return redirect(url_for("iot.devices"))

    return render_template(
        "admin/perangkat.html",
        devices=IotDevice.query.order_by(IotDevice.kode).all(),
        sources=WaterSource.query.order_by(WaterSource.nama).all(),
        online=device_is_online,
        one_time_key=None,
    )


@iot_bp.post("/admin/telemetri/perangkat/<int:device_id>/toggle")
@role_required("admin")
def toggle_device(device_id):
    device = db.session.get(IotDevice, device_id)
    if device is None:
        from flask import abort

        abort(404)
    device.aktif = not device.aktif
    db.session.commit()
    flash(f"Perangkat {device.kode} sekarang {'aktif' if device.aktif else 'nonaktif'}.", "success")
    return redirect(url_for("iot.devices"))


@iot_bp.post("/admin/telemetri/perangkat/<int:device_id>/hapus")
@role_required("admin")
def remove_device(device_id):
    code = delete_device(device_id)
    if code is None:
        from flask import abort

        abort(404)
    flash(f"Perangkat {code} dan riwayat bacaannya dihapus.", "success")
    return redirect(url_for("iot.devices"))


@iot_bp.get("/api/telemetry/series/<int:device_id>")
@role_required("warga", "petugas_lab", "admin")
def telemetry_series(device_id):
    device = db.session.get(IotDevice, device_id)
    if device is None:
        from flask import abort

        abort(404)
    return jsonify(
        {
            "device_id": device.id,
            "kode": device.kode,
            "online": device_is_online(device),
            "series": [
                {
                    "id": reading.id,
                    "ph": reading.ph,
                    "kekeruhan_ntu": reading.kekeruhan_ntu,
                    "tds_mgl": reading.tds_mgl,
                    "vonis": reading.vonis,
                    "diterima_at": reading.diterima_at.isoformat(),
                }
                for reading in sensor_series(device_id).traverse()
            ],
        }
    )
