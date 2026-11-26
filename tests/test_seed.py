import json
from pathlib import Path

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
)
from seed import DEMO_API_KEYS, seed_database


def test_seed_is_idempotent_and_creates_required_demo_data(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'seed.db'}",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
        seed_database()
        seed_database()

        assert User.query.count() == 3
        region_snapshot = json.loads(
            (Path(__file__).parents[1] / "data" / "nyata" / "wilayah_administratif.json")
            .read_text(encoding="utf-8")
        )
        assert Region.query.count() == len(region_snapshot["regions"])
        assert WaterSource.query.count() == 19
        assert WaterSource.query.filter_by(is_simulated=True).count() == 15
        assert WaterSource.query.filter_by(
            is_simulated=False, sumber_data="osm"
        ).count() == 4
        assert (
            WaterSource.query.filter_by(is_simulated=False, region_id=None).count()
            == 4
        )
        assert RiverEdge.query.filter_by(terverifikasi=True).count() == 3
        assert RiverEdge.query.filter_by(sumber_jarak="simulasi").count() == 14
        assert Sample.query.count() == 10
        assert TestResult.query.count() == 4
        assert IotDevice.query.count() == 4
        assert SensorReading.query.count() == 30
        assert set(device.kode for device in IotDevice.query.all()) == set(DEMO_API_KEYS)
        assert all(
            device.source.is_simulated and device.source.sumber_data == "simulasi"
            for device in IotDevice.query.all()
        )
        assert all(
            result.sumber_data == "simulasi"
            for result in TestResult.query.all()
        )
        assert all(
            source.region_id is None
            for source in WaterSource.query.filter_by(is_simulated=True).all()
        )
