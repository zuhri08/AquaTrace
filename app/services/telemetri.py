import hashlib
import hmac
import json
import math
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError

from app import db
from app.ds.linked_list import LinkedList
from app.ds.queue import Queue
from app.models import IotDevice, Sample, SensorReading, WaterSource, utcnow
from app.services.diagnosis import evaluate_measurements, validate_measurements

RATE_LIMIT_SECONDS = 2
OFFLINE_AFTER_MINUTES = 5
DEFAULT_SERIES_WINDOW = 20


class IngestError(Exception):
    """Expected API ingestion failure with an HTTP status and field details."""

    def __init__(self, message, status_code, fields=None):
        super().__init__(message)
        self.status_code = status_code
        self.fields = fields or {}


def _parse_sensor_timestamp(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise IngestError("Format ts harus ISO-8601.", 422, {"ts": "Format ISO-8601 wajib."})
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as error:
        raise IngestError("Format ts harus ISO-8601.", 422, {"ts": "Format ISO-8601 tidak valid."}) from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _validated_measurements(payload):
    try:
        return validate_measurements(payload)
    except ValueError as error:
        try:
            fields = json.loads(str(error))
        except json.JSONDecodeError:
            fields = {"pengukuran": str(error)}
        raise IngestError("Nilai pengukuran tidak valid.", 422, fields) from error


def build_reading_queue():
    """Build the telemetry FIFO from pending database readings."""
    queue = Queue()
    for reading in (
        SensorReading.query.filter_by(status="antri")
        .order_by(SensorReading.diterima_at.asc(), SensorReading.id.asc())
        .all()
    ):
        queue.enqueue(reading)
    return queue


def accept_reading(code, api_key, payload):
    """Authenticate and persist one validated telemetry reading in FIFO order."""
    if not isinstance(payload, dict):
        raise IngestError("Body harus berupa objek JSON.", 422, {"body": "JSON object wajib."})
    if not isinstance(code, str) or not code.strip():
        code = payload.get("kode")
    if not isinstance(code, str) or not code.strip():
        raise IngestError("Kode perangkat wajib diisi.", 422, {"kode": "Wajib diisi."})
    if not isinstance(api_key, str) or not api_key:
        api_key = ""
    device = IotDevice.query.filter_by(kode=code.strip()).first()
    supplied_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    expected_hash = device.api_key_hash if device is not None else "0" * 64
    key_matches = hmac.compare_digest(supplied_hash, expected_hash)
    if device is None or not key_matches:
        raise IngestError("API key tidak valid.", 401)
    if not device.aktif:
        raise IngestError("Perangkat tidak aktif.", 401)

    for field in ("ph", "kekeruhan_ntu", "tds_mgl"):
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise IngestError(
                "Nilai pengukuran harus berupa angka JSON.",
                422,
                {field: "Masukkan nilai angka."},
            )
    measurements = _validated_measurements(payload)
    timestamp = _parse_sensor_timestamp(payload.get("ts"))
    received_at = utcnow()
    if timestamp is not None and SensorReading.query.filter_by(
        device_id=device.id, ts_sensor=timestamp
    ).first():
        raise IngestError(
            "Bacaan dengan timestamp ini sudah diterima.",
            422,
            {"ts": "Timestamp duplikat untuk perangkat ini."},
        )

    try:
        dialect = db.session.get_bind().dialect.name
        if dialect == "mysql":
            locked_device = (
                IotDevice.query.filter_by(id=device.id).with_for_update().first()
            )
            if locked_device is None or not locked_device.aktif:
                raise IngestError("Perangkat tidak aktif.", 401)
            if (
                locked_device.last_ingested_at is not None
                and (received_at - locked_device.last_ingested_at).total_seconds()
                < RATE_LIMIT_SECONDS
            ):
                raise IngestError("Batas laju perangkat terlampaui.", 429)
            locked_device.last_ingested_at = received_at
            locked_device.last_seen = received_at
            locked_device.source_id = device.source_id
        else:
            cutoff = received_at - timedelta(seconds=RATE_LIMIT_SECONDS)
            updated_id = db.session.execute(
                update(IotDevice)
                .where(
                    IotDevice.id == device.id,
                    IotDevice.aktif.is_(True),
                    or_(
                        IotDevice.last_ingested_at.is_(None),
                        IotDevice.last_ingested_at <= cutoff,
                    ),
                )
                .values(last_ingested_at=received_at, last_seen=received_at)
                .returning(IotDevice.id)
            ).scalar_one_or_none()
            if updated_id is None:
                db.session.rollback()
                active_device = db.session.get(IotDevice, device.id)
                if active_device is None or not active_device.aktif:
                    raise IngestError("Perangkat tidak aktif.", 401)
                raise IngestError("Batas laju perangkat terlampaui.", 429)

        reading = SensorReading(
            device_id=device.id,
            source_id=device.source_id,
            ph=measurements["ph"],
            kekeruhan_ntu=measurements["kekeruhan_ntu"],
            tds_mgl=measurements["tds_mgl"],
            status="antri",
            ts_sensor=timestamp,
            diterima_at=received_at,
        )
        db.session.add(reading)
        db.session.flush()
        queue = build_reading_queue()
        position = next(
            index
            for index, queued in enumerate(queue.to_list(), start=1)
            if queued.id == reading.id
        )
        db.session.commit()
        return {"reading_id": reading.id, "posisi_antrean": position}
    except IngestError:
        db.session.rollback()
        raise
    except IntegrityError as error:
        db.session.rollback()
        if timestamp is not None:
            raise IngestError(
                "Bacaan dengan timestamp ini sudah diterima.",
                422,
                {"ts": "Timestamp duplikat untuk perangkat ini."},
            ) from error
        raise
    except Exception:
        db.session.rollback()
        raise


def _claim_reading(reading_id):
    now = utcnow()
    if db.session.get_bind().dialect.name == "mysql":
        reading = (
            SensorReading.query.filter_by(id=reading_id, status="antri")
            .with_for_update()
            .first()
        )
        if reading is None:
            db.session.rollback()
            return None
        reading.status = "diproses"
        reading.diproses_at = now
        return reading
    claimed_id = db.session.execute(
        update(SensorReading)
        .where(SensorReading.id == reading_id, SensorReading.status == "antri")
        .values(status="diproses", diproses_at=now)
        .returning(SensorReading.id)
    ).scalar_one_or_none()
    if claimed_id is None:
        db.session.rollback()
        return None
    return db.session.get(SensorReading, claimed_id)


def process_reading(reading_id):
    """Claim, evaluate, and persist one telemetry item and any triggered sample."""
    try:
        reading = _claim_reading(reading_id)
        if reading is None:
            return None
        if db.session.get_bind().dialect.name != "mysql":
            # A no-op write serializes same-source decisions in SQLite.
            db.session.execute(
                update(WaterSource)
                .where(WaterSource.id == reading.source_id)
                .values(status_sensor=WaterSource.status_sensor)
            )
        source = (
            WaterSource.query.filter_by(id=reading.source_id)
            .with_for_update()
            .first()
        )
        device = db.session.get(IotDevice, reading.device_id)
        if source is None or device is None:
            raise RuntimeError("Perangkat atau sumber telemetri tidak ditemukan.")
        verdict, trace = evaluate_measurements(
            {
                "ph": reading.ph,
                "kekeruhan_ntu": reading.kekeruhan_ntu,
                "tds_mgl": reading.tds_mgl,
            }
        )
        reading.vonis = verdict
        reading.jejak_keputusan = " → ".join(trace)
        source.status_sensor = verdict
        device.last_seen = utcnow()
        triggered_sample = None
        if verdict == "TIDAK_LAYAK":
            open_sample = Sample.query.filter(
                Sample.source_id == source.id,
                Sample.status.in_(("menunggu", "diproses")),
            ).first()
            if open_sample is None:
                triggered_sample = Sample(
                    source_id=source.id,
                    diajukan_oleh=None,
                    asal="iot",
                    prioritas=True,
                    status="menunggu",
                )
                db.session.add(triggered_sample)
                db.session.flush()
        db.session.commit()
        return {
            "reading_id": reading.id,
            "vonis": verdict,
            "sample_id": triggered_sample.id if triggered_sample else None,
        }
    except Exception:
        db.session.rollback()
        raise


def process_reading_queue(limit=None):
    """Dequeue pending readings FIFO and process up to optional item limit."""
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
        raise ValueError("limit harus bilangan bulat positif.")
    queue = build_reading_queue()
    processed = []
    while not queue.is_empty() and (limit is None or len(processed) < limit):
        reading = queue.dequeue()
        result = process_reading(reading.id)
        if result is not None:
            processed.append(result)
    return processed


def sensor_series(device_id, window=DEFAULT_SERIES_WINDOW):
    """Return the latest N readings in a LinkedList in chronological order."""
    if isinstance(window, bool) or not isinstance(window, int) or window < 1:
        raise ValueError("window harus bilangan bulat positif.")
    rows = (
        SensorReading.query.filter_by(device_id=device_id)
        .order_by(SensorReading.diterima_at.desc(), SensorReading.id.desc())
        .limit(window)
        .all()
    )
    series = LinkedList(id_getter=lambda reading: reading.id)
    for reading in reversed(rows):
        series.insert_tail(reading)
        if series.length() > window:
            series.remove_head()
    return series


def latest_readings(limit=50):
    """Return recent readings for a read-only feed."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit harus bilangan bulat positif.")
    return (
        SensorReading.query.order_by(
            SensorReading.diterima_at.desc(), SensorReading.id.desc()
        )
        .limit(limit)
        .all()
    )


def device_is_online(device, now=None):
    """A device is online only if an accepted reading arrived within five minutes."""
    if device.last_seen is None:
        return False
    now = now or utcnow()
    return now - device.last_seen <= timedelta(minutes=OFFLINE_AFTER_MINUTES)


def register_device(source_id, code, name):
    """Create an IoT device and return its one-time plaintext API key."""
    if not isinstance(code, str) or not code.strip() or len(code.strip()) > 80:
        raise ValueError("Kode perangkat wajib diisi (maksimal 80 karakter).")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        raise ValueError("Nama perangkat wajib diisi (maksimal 120 karakter).")
    if db.session.get(WaterSource, source_id) is None:
        raise ValueError("Sumber air tidak ditemukan.")
    if IotDevice.query.filter_by(kode=code.strip()).first():
        raise ValueError("Kode perangkat sudah digunakan.")
    api_key = secrets.token_urlsafe(32)
    device = IotDevice(
        source_id=source_id,
        kode=code.strip(),
        nama=name.strip(),
        api_key_hash=hashlib.sha256(api_key.encode("utf-8")).hexdigest(),
        aktif=True,
    )
    db.session.add(device)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ValueError("Kode perangkat sudah digunakan.") from error
    return device, api_key


def delete_device(device_id):
    """Delete a device and its telemetry history."""
    device = db.session.get(IotDevice, device_id)
    if device is None:
        return None
    code = device.kode
    for reading in device.readings:
        db.session.delete(reading)
    db.session.delete(device)
    db.session.commit()
    return code
