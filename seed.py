import hashlib
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.data_migrations import ensure_phase_d_schema
from app.models import (
    IotDevice,
    Region,
    RiverEdge,
    Sample,
    SensorReading,
    TestResult,
    User,
    WaterSource,
    utcnow,
)

DEMO_API_KEYS = {
    "SENSOR-01": "demo-sensor-01-key",
    "SENSOR-02": "demo-sensor-02-key",
    "SENSOR-03": "demo-sensor-03-key",
    "SENSOR-04": "demo-sensor-04-key",
}


def _get_or_create(model, lookup, values):
    item = model.query.filter_by(**lookup).first()
    if item is None:
        item = model(**lookup, **values)
        db.session.add(item)
        db.session.flush()
    return item


def _seed_official_regions():
    path = (
        Path(__file__).resolve().parent
        / "data"
        / "nyata"
        / "wilayah_administratif.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"Snapshot wilayah resmi tidak ditemukan: {path}")
    with path.open(encoding="utf-8") as file:
        snapshot = json.load(file)

    regions_by_code = {}
    for row in snapshot["regions"]:
        parent = regions_by_code.get(row["parent_code"])
        region = _get_or_create(
            Region,
            {
                "nama": row["nama"],
                "level": row["level"],
                "parent_id": parent.id if parent else None,
            },
            {},
        )
        regions_by_code[row["kode_bps"]] = region
    return regions_by_code


def _seed_osm_network(regions_by_code):
    path = (
        Path(__file__).resolve().parent
        / "data"
        / "nyata"
        / "osm_river_geometry.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"Snapshot geometri OSM tidak ditemukan: {path}")
    with path.open(encoding="utf-8") as file:
        snapshot = json.load(file)

    sources_by_key = {}
    for row in snapshot["sources"]:
        references = " ".join(row["referensi"])
        source = _get_or_create(
            WaterSource,
            {"nama": row["name"]},
            {
                "tipe": row["type"],
                "region_id": (
                    regions_by_code[row["region_code"]].id
                    if row["region_code"] in regions_by_code
                    else None
                ),
                "lat": row["lat"],
                "lng": row["lng"],
                "status_terakhir": "belum_diuji",
                "status_sensor": "belum_ada",
                "sumber_data": row["source_data"],
                "is_simulated": row["is_simulated"],
                "referensi": references,
                "dibuat_oleh": None,
            },
        )
        source.tipe = row["type"]
        source.region_id = (
            regions_by_code[row["region_code"]].id
            if row["region_code"] in regions_by_code
            else None
        )
        source.lat = row["lat"]
        source.lng = row["lng"]
        source.status_terakhir = "belum_diuji"
        source.status_sensor = "belum_ada"
        source.sumber_data = row["source_data"]
        source.is_simulated = row["is_simulated"]
        source.referensi = references
        sources_by_key[row["key"]] = source

    edge_count = 0
    for row in snapshot["edges"]:
        source = sources_by_key[row["from"]]
        target = sources_by_key[row["to"]]
        edge = _get_or_create(
            RiverEdge,
            {"dari_source_id": source.id, "ke_source_id": target.id},
            {
                "jarak_km": row["jarak_km"],
                "sumber_jarak": row["sumber_jarak"],
                "terverifikasi": row["terverifikasi"],
            },
        )
        edge.jarak_km = row["jarak_km"]
        edge.sumber_jarak = row["sumber_jarak"]
        edge.terverifikasi = row["terverifikasi"]
        edge_count += 1
    return {"sources": len(sources_by_key), "edges": edge_count}


def seed_database():
    ensure_phase_d_schema()
    ensure_telemetry_schema()
    users = {}
    for email, name, role in (
        ("admin@aquatrace.test", "Admin Demo", "admin"),
        ("petugas@aquatrace.test", "Petugas Demo", "petugas_lab"),
        ("warga@aquatrace.test", "Warga Demo", "warga"),
    ):
        users[role] = _get_or_create(
            User,
            {"email": email},
            {
                "nama": name,
                "password_hash": generate_password_hash("AquaTraceDemo123!"),
                "role": role,
                "aktif": True,
            },
        )

    sources = []
    types = ("sumur", "sungai", "pdam", "mata_air")
    for index in range(15):
        source = _get_or_create(
            WaterSource,
            {"nama": f"Sumber Simulasi {index + 1:02d}"},
            {
                "tipe": types[index % len(types)],
                "region_id": None,
                "lat": None,
                "lng": None,
                "status_terakhir": "belum_diuji",
                "status_sensor": "belum_ada",
                "sumber_data": "simulasi",
                "is_simulated": True,
                "referensi": "DEMO/SIMULASI; koordinat tidak disediakan.",
                "dibuat_oleh": users["warga"].id,
            },
        )
        source.region_id = None
        source.lat = None
        source.lng = None
        source.sumber_data = "simulasi"
        source.is_simulated = True
        source.referensi = "DEMO/SIMULASI; koordinat tidak disediakan."
        sources.append(source)

    for index in range(14):
        _get_or_create(
            RiverEdge,
            {"dari_source_id": sources[index].id, "ke_source_id": sources[index + 1].id},
            {
                "jarak_km": round(0.5 + (index % 5) * 0.25, 2),
                "sumber_jarak": "simulasi",
                "terverifikasi": False,
            },
        )

    sample_specs = (
        ("menunggu", True),
        ("menunggu", False),
        ("menunggu", True),
        ("menunggu", False),
        ("diproses", False),
        ("diproses", False),
        ("selesai", False),
        ("selesai", False),
        ("selesai", False),
        ("selesai", False),
    )
    verdicts = ("BERSIH", "WASPADA", "TIDAK_LAYAK", "BERSIH")
    for index, (status, priority) in enumerate(sample_specs):
        sample = _get_or_create(
            Sample,
            {"id": index + 1},
            {
                "source_id": sources[index].id,
                "diajukan_oleh": users["warga"].id,
                "asal": "warga",
                "prioritas": priority,
                "status": status,
                "created_at": utcnow() - timedelta(minutes=10 - index),
            },
        )
        if status == "selesai":
            result_index = index - 6
            _get_or_create(
                TestResult,
                {"sample_id": sample.id},
                {
                    "source_id": sample.source_id,
                    "ph": (6.8, 7.1, 5.9, 7.4)[result_index],
                    "kekeruhan_ntu": (1.2, 8.5, 28.0, 3.1)[result_index],
                    "tds_mgl": (120, 210, 510, 180)[result_index],
                    "vonis": verdicts[result_index],
                    "jejak_keputusan": (
                        f"Data simulasi hasil uji #{index + 1}; screening, "
                        "bukan pengganti uji laboratorium lengkap."
                    ),
                    "diuji_oleh": users["petugas_lab"].id,
                    "sumber_data": "simulasi",
                    "referensi": "DEMO/SIMULASI; seed AquaTrace.",
                    "tanggal_pengambilan": None,
                },
            )
            result = TestResult.query.filter_by(sample_id=sample.id).one()
            result.sumber_data = "simulasi"
            result.referensi = "DEMO/SIMULASI; seed AquaTrace."
            result.tanggal_pengambilan = None
            sample.source.status_terakhir = verdicts[result_index]

    rng = random.Random(42)
    devices = []
    for index, (code, raw_key) in enumerate(DEMO_API_KEYS.items()):
        device = _get_or_create(
            IotDevice,
            {"kode": code},
            {
                "source_id": sources[index + 10].id,
                "nama": f"Sensor Simulasi {index + 1}",
                "api_key_hash": hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
                "aktif": True,
                "last_seen": utcnow(),
            },
        )
        device.source.is_simulated = True
        device.source.sumber_data = "simulasi"
        devices.append(device)

    seed_reading_start = datetime(2025, 1, 1, 12, 0)
    for index in range(30):
        device = devices[index % len(devices)]
        key = {
            "device_id": device.id,
            "diterima_at": seed_reading_start + timedelta(minutes=index),
        }
        if SensorReading.query.filter_by(**key).first() is None:
            db.session.add(
                SensorReading(
                    **key,
                    source_id=device.source_id,
                    ph=round(rng.uniform(6.5, 8.2), 2),
                    kekeruhan_ntu=round(rng.uniform(0.2, 12.0), 2),
                    tds_mgl=round(rng.uniform(80, 450), 2),
                    status="diproses",
                    vonis=("BERSIH", "WASPADA", "BERSIH")[index % 3],
                    jejak_keputusan="Bacaan simulasi seed; ambang contoh belum ditetapkan.",
                    diproses_at=seed_reading_start + timedelta(minutes=index),
                )
            )

    real_data = _seed_official_regions()
    real_network = _seed_osm_network(real_data)
    db.session.commit()
    return {
        "users": len(users),
        "regions": Region.query.count(),
        "sources": WaterSource.query.count(),
        "real_sources": real_network["sources"],
        "real_edges": real_network["edges"],
    }


def ensure_telemetry_schema():
    """Apply additive IoT columns/indexes when upgrading an existing demo DB."""
    dialect = db.session.get_bind().dialect.name
    if dialect not in {"sqlite", "mysql"}:
        return
    inspector = inspect(db.engine)
    if not inspector.has_table("iot_devices") or not inspector.has_table("sensor_readings"):
        return
    device_columns = {column["name"] for column in inspector.get_columns("iot_devices")}
    reading_columns = {
        column["name"] for column in inspector.get_columns("sensor_readings")
    }
    with db.engine.begin() as connection:
        if "last_ingested_at" not in device_columns:
            connection.execute(
                text("ALTER TABLE iot_devices ADD COLUMN last_ingested_at DATETIME")
            )
        if "ts_sensor" not in reading_columns:
            connection.execute(
                text("ALTER TABLE sensor_readings ADD COLUMN ts_sensor DATETIME")
            )
        indexes = {
            index["name"] for index in inspect(db.engine).get_indexes("sensor_readings")
        }
        constraints = {
            item.get("name")
            for item in inspect(db.engine).get_unique_constraints("sensor_readings")
        }
        if (
            "uq_sensor_readings_device_timestamp" not in indexes
            and "uq_sensor_readings_device_timestamp" not in constraints
        ):
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX uq_sensor_readings_device_timestamp "
                    "ON sensor_readings (device_id, ts_sensor)"
                )
            )


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_database()
        print("Seed selesai. Kredensial demo:")
        print("Semua role: password AquaTraceDemo123!")
        print("admin@aquatrace.test | petugas@aquatrace.test | warga@aquatrace.test")
        print("API key demo (hanya hash disimpan):")
        for code, key in DEMO_API_KEYS.items():
            print(f"{code}: {key}")


if __name__ == "__main__":
    main()
