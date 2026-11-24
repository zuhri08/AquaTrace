import hashlib
import random
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app import create_app, db
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


def seed_database():
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

    province = _get_or_create(
        Region, {"nama": "Provinsi Simulasi"}, {"level": "provinsi", "parent_id": None}
    )
    cities = [
        _get_or_create(
            Region,
            {"nama": f"Kota Simulasi {i}"},
            {"level": "kota", "parent_id": province.id},
        )
        for i in range(1, 3)
    ]
    villages = []
    for city_index, city in enumerate(cities, start=1):
        for subdistrict_index in range(1, 3):
            subdistrict = _get_or_create(
                Region,
                {"nama": f"Kecamatan {city_index}-{subdistrict_index}"},
                {"level": "kecamatan", "parent_id": city.id},
            )
            for village_index in range(1, 3):
                villages.append(
                    _get_or_create(
                        Region,
                        {"nama": f"Desa {city_index}-{subdistrict_index}-{village_index}"},
                        {"level": "desa", "parent_id": subdistrict.id},
                    )
                )

    sources = []
    types = ("sumur", "sungai", "pdam", "mata_air")
    for index in range(15):
        source = _get_or_create(
            WaterSource,
            {"nama": f"Sumber Simulasi {index + 1:02d}"},
            {
                "tipe": types[index % len(types)],
                "region_id": villages[index % len(villages)].id,
                "lat": -7.25 + index * 0.001,
                "lng": 112.75 + index * 0.001,
                "status_terakhir": "belum_diuji",
                "status_sensor": "belum_ada",
                "dibuat_oleh": users["warga"].id,
            },
        )
        sources.append(source)

    for index in range(14):
        _get_or_create(
            RiverEdge,
            {"dari_source_id": sources[index].id, "ke_source_id": sources[index + 1].id},
            {"jarak_km": round(0.5 + (index % 5) * 0.25, 2)},
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
                },
            )
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

    db.session.commit()
    return {"users": len(users), "regions": len(villages) + 7, "sources": len(sources)}


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
