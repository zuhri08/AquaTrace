from app import create_app, db
from app import models
from app.models import IotDevice, Region, Sample, SensorReading, User, WaterSource
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
        assert Region.query.count() == 15
        assert WaterSource.query.count() == 15
        assert Sample.query.count() == 10
        assert models.TestResult.query.count() == 4
        assert IotDevice.query.count() == 4
        assert SensorReading.query.count() == 30
        assert set(device.kode for device in IotDevice.query.all()) == set(DEMO_API_KEYS)
