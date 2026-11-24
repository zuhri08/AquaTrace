import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest

from app import create_app, db
from app.models import IotDevice, Sample, SensorReading, User, WaterSource, utcnow
from app.services.telemetri import (
    IngestError,
    accept_reading,
    build_reading_queue,
    device_is_online,
    process_reading_queue,
    register_device,
    sensor_series,
)
from iot_simulator import build_payload
from seed import seed_database


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "iot-test-secret",
            "IOT_AUTO_PROSES": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'iot.db'}",
        }
    )
    with application.app_context():
        db.create_all()
        seed_database()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _payload(code="SENSOR-01", **values):
    return {
        "kode": code,
        "ph": 7.2,
        "kekeruhan_ntu": 1.8,
        "tds_mgl": 145.0,
        "ts": "2026-11-24T12:00:00+00:00",
        **values,
    }


def _login(client, email="admin@aquatrace.test"):
    response = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    ).group(1)
    return client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": email,
            "password": "AquaTraceDemo123!",
        },
    )


def test_ingest_auth_validation_timestamp_dedup_and_rate_limit(app):
    client = app.test_client()
    missing_key = client.post("/api/iot/ingest", json=_payload())
    assert missing_key.status_code == 401
    wrong = client.post(
        "/api/iot/ingest",
        json=_payload(),
        headers={"X-API-Key": "wrong"},
    )
    assert wrong.status_code == 401

    invalid = _payload(ph=14.1)
    rejected = client.post(
        "/api/iot/ingest",
        json=invalid,
        headers={"X-API-Key": "demo-sensor-01-key"},
    )
    assert rejected.status_code == 422
    assert "ph" in rejected.json["fields"]

    not_numeric = client.post(
        "/api/iot/ingest",
        json=_payload(ph=True),
        headers={"X-API-Key": "demo-sensor-01-key"},
    )
    assert not_numeric.status_code == 422
    invalid_timestamp = client.post(
        "/api/iot/ingest",
        json=_payload(ts="not-a-timestamp"),
        headers={"X-API-Key": "demo-sensor-01-key"},
    )
    assert invalid_timestamp.status_code == 422
    assert "ts" in invalid_timestamp.json["fields"]

    accepted = client.post(
        "/api/iot/ingest",
        json=_payload(),
        headers={"X-API-Key": "demo-sensor-01-key"},
    )
    assert accepted.status_code == 202
    assert accepted.json["status"] == "antri"
    assert accepted.json["posisi_antrean"] == 1

    duplicate = client.post(
        "/api/iot/ingest",
        json=_payload(),
        headers={"X-API-Key": "demo-sensor-01-key"},
    )
    assert duplicate.status_code == 422
    assert "duplikat" in duplicate.json["fields"]["ts"]

    limited = client.post(
        "/api/iot/ingest",
        json=_payload(ts="2026-11-24T12:00:01+00:00"),
        headers={"X-API-Key": "demo-sensor-01-key"},
    )
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "2"

    with app.app_context():
        device = IotDevice.query.filter_by(kode="SENSOR-01").one()
        device.aktif = False
        db.session.commit()
    inactive = client.post(
        "/api/iot/ingest",
        json=_payload(ts="2026-11-24T12:00:04+00:00"),
        headers={"X-API-Key": "demo-sensor-01-key"},
    )
    assert inactive.status_code == 401


def test_concurrent_ingest_enforces_per_device_rate_limit_atomically(app):
    barrier = Barrier(2)

    def ingest(index):
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                return accept_reading(
                    "SENSOR-01",
                    "demo-sensor-01-key",
                    _payload(ts=f"2026-11-24T12:00:0{index}Z"),
                )
            except IngestError as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(ingest, (1, 2)))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count(429) == 1
    with app.app_context():
        assert SensorReading.query.filter_by(
            device_id=IotDevice.query.filter_by(kode="SENSOR-01").one().id,
            status="antri",
        ).count() == 1


def test_queue_processes_fifo_and_uses_same_diagnosis_tree(app):
    with app.app_context():
        first = accept_reading(
            "SENSOR-01",
            "demo-sensor-01-key",
            _payload(ts="2026-11-24T12:01:00Z"),
        )
        second = accept_reading(
            "SENSOR-02",
            "demo-sensor-02-key",
            _payload(
                "SENSOR-02",
                ph=7.1,
                kekeruhan_ntu=9.0,
                ts="2026-11-24T12:01:01Z",
            ),
        )
        queue = build_reading_queue()
        assert [reading.id for reading in queue.to_list()] == [
            first["reading_id"],
            second["reading_id"],
        ]
        results = process_reading_queue()
        assert [item["reading_id"] for item in results] == [
            first["reading_id"],
            second["reading_id"],
        ]
        assert [item["vonis"] for item in results] == ["BERSIH", "WASPADA"]
        rows = [
            db.session.get(SensorReading, first["reading_id"]),
            db.session.get(SensorReading, second["reading_id"]),
        ]
        assert all(row.status == "diproses" and row.diproses_at for row in rows)
        assert rows[0].jejak_keputusan
        assert rows[0].source.status_sensor == "BERSIH"


def test_contaminated_sensor_creates_one_priority_sample_without_duplicates(app):
    with app.app_context():
        first_device = IotDevice.query.filter_by(kode="SENSOR-01").one()
        second_device = IotDevice.query.filter_by(kode="SENSOR-02").one()
        second_device.source_id = first_device.source_id
        db.session.commit()
        source_id = first_device.source_id
        first = accept_reading(
            "SENSOR-01",
            "demo-sensor-01-key",
            _payload(ph=4.0, ts="2026-11-24T12:02:00Z"),
        )
        result = process_reading_queue()
        assert result[0]["reading_id"] == first["reading_id"]
        assert result[0]["vonis"] == "TIDAK_LAYAK"
        assert result[0]["sample_id"] is not None
        source = db.session.get(WaterSource, source_id)
        assert source.status_sensor == "TIDAK_LAYAK"
        first_sample = Sample.query.filter_by(
            source_id=source_id, asal="iot", status="menunggu"
        ).one()
        assert first_sample.prioritas is True
        assert first_sample.diajukan_oleh is None

        first_device.last_ingested_at = utcnow() - timedelta(seconds=3)
        db.session.commit()
        accept_reading(
            "SENSOR-01",
            "demo-sensor-01-key",
            _payload(ph=4.1, ts="2026-11-24T12:02:02Z"),
        )
        second_device.last_ingested_at = utcnow() - timedelta(seconds=3)
        db.session.commit()
        accept_reading(
            "SENSOR-02",
            "demo-sensor-02-key",
            _payload("SENSOR-02", ph=4.2, ts="2026-11-24T12:02:03Z"),
        )
        processed = process_reading_queue()
        assert len(processed) == 2
        assert Sample.query.filter_by(
            source_id=source_id, asal="iot", status="menunggu"
        ).count() == 1


def test_sensor_series_is_bounded_linked_list_and_device_online_timeout(app):
    with app.app_context():
        device = IotDevice.query.filter_by(kode="SENSOR-01").one()
        series = sensor_series(device.id, window=3)
        values = series.traverse()
        assert series.length() == 3
        assert [item.diterima_at for item in values] == sorted(
            item.diterima_at for item in values
        )

        device.last_seen = utcnow() - timedelta(minutes=6)
        assert not device_is_online(device)
        device.last_seen = utcnow() - timedelta(minutes=4)
        assert device_is_online(device)
        device.last_seen = None
        assert not device_is_online(device)


def test_admin_device_key_is_hashed_and_displayed_once(app):
    with app.app_context():
        source = WaterSource.query.order_by(WaterSource.id).first()
        device, raw_key = register_device(source.id, "SENSOR-NEW", "Sensor Baru")
        assert device.api_key_hash == hashlib.sha256(raw_key.encode()).hexdigest()
        assert raw_key not in device.api_key_hash
        device_id = device.id

    client = app.test_client()
    assert _login(client).status_code == 302
    page = client.get("/admin/telemetri/perangkat")
    csrf = re.search(
        r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)
    ).group(1)
    created = client.post(
        "/admin/telemetri/perangkat",
        data={
            "csrf_token": csrf,
            "source_id": "1",
            "kode": "SENSOR-WEB",
            "nama": "Sensor Web",
        },
    )
    assert created.status_code == 201
    assert b"Simpan API key berikut sekarang" in created.data
    raw_key = re.search(rb"<code>([^<]+)</code>", created.data).group(1).decode()
    assert raw_key not in created.headers.get("Set-Cookie", "")
    second_page = client.get("/admin/telemetri/perangkat")
    assert raw_key.encode() not in second_page.data
    with app.app_context():
        assert db.session.get(IotDevice, device_id) is not None


def test_admin_can_deactivate_and_delete_device_with_readings(app):
    client = app.test_client()
    assert _login(client).status_code == 302
    with app.app_context():
        device = IotDevice.query.filter_by(kode="SENSOR-04").one()
        device_id = device.id
        assert SensorReading.query.filter_by(device_id=device_id).count() > 0

    page = client.get("/admin/telemetri/perangkat")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)
    ).group(1)
    disabled = client.post(
        f"/admin/telemetri/perangkat/{device_id}/toggle",
        data={"csrf_token": token},
    )
    assert disabled.status_code == 302
    with app.app_context():
        assert db.session.get(IotDevice, device_id).aktif is False

    page = client.get("/admin/telemetri/perangkat")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)
    ).group(1)
    deleted = client.post(
        f"/admin/telemetri/perangkat/{device_id}/hapus",
        data={"csrf_token": token},
    )
    assert deleted.status_code == 302
    with app.app_context():
        assert db.session.get(IotDevice, device_id) is None
        assert SensorReading.query.filter_by(device_id=device_id).count() == 0


def test_auto_process_and_public_feed_do_not_require_login(app):
    app.config["IOT_AUTO_PROSES"] = True
    client = app.test_client()
    response = client.post(
        "/api/iot/ingest",
        json=_payload(ph=4, ts="2026-11-24T12:03:00Z"),
        headers={"X-API-Key": "demo-sensor-01-key"},
    )
    assert response.status_code == 202
    with app.app_context():
        reading = db.session.get(SensorReading, response.json["reading_id"])
        assert reading.status == "diproses"
        assert reading.vonis == "TIDAK_LAYAK"
        assert Sample.query.filter_by(
            source_id=reading.source_id, asal="iot", status="menunggu"
        ).count() == 1
    public = client.get("/publik/telemetri")
    assert public.status_code == 200
    assert b"DATA SIMULASI" in public.data
    assert _login(client, "petugas@aquatrace.test").status_code == 302
    staff_page = client.get("/petugas/telemetri")
    assert staff_page.status_code == 200
    series = client.get("/api/telemetry/series/1")
    assert series.status_code == 200
    assert "series" in series.json


def test_staff_manual_queue_processing_page(app):
    client = app.test_client()
    accepted = client.post(
        "/api/iot/ingest",
        json=_payload(ts="2026-11-24T12:04:00Z"),
        headers={"X-API-Key": "demo-sensor-01-key"},
    )
    assert accepted.status_code == 202
    assert _login(client, "petugas@aquatrace.test").status_code == 302
    page = client.get("/petugas/telemetri")
    assert page.status_code == 200
    assert b"Antrean FIFO" in page.data
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)
    ).group(1)
    processed = client.post(
        "/petugas/telemetri/proses", data={"csrf_token": token}
    )
    assert processed.status_code == 302
    with app.app_context():
        reading = db.session.get(SensorReading, accepted.json["reading_id"])
        assert reading.status == "diproses"
        assert reading.vonis == "BERSIH"


def test_simulator_scenarios_produce_expected_demo_readings():
    normal = build_payload("SENSOR-01", "normal", 0)
    contaminated = build_payload("SENSOR-01", "tercemar", 0)
    drift_first = build_payload("SENSOR-01", "drift", 0)
    drift_later = build_payload("SENSOR-01", "drift", 3)
    assert normal["ph"] == 7.2
    assert contaminated["ph"] < 6.5
    assert drift_later["kekeruhan_ntu"] > drift_first["kekeruhan_ntu"]
